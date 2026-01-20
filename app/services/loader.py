from pathlib import Path
import pandas as pd
import json
import uuid
import pdfplumber
import logging
from app.core.cache import cache
from app.services.semantic_chunking import create_enhanced_chunks
from app.core.validation import DataIntegrityValidator, validate_and_log
from app.utils.data_mapper import normalize_park, normalize_plot, get_field_value

logger = logging.getLogger(__name__)

BASE = Path("app/data/states")


def _normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize DataFrame columns to match expected field names.
    Handles case-insensitive matching and column aliases.
    """
    col_mapping = {
        'plotno': 'plot_number',
        'plotnumber': 'plot_number',
        'plot_no': 'plot_number',
        'plotrate': 'rate',
        'plot_rate': 'rate',
        'plotsize': 'size_sq_m',
        'plot_size': 'size_sq_m',
        'plotstatus': 'status',
        'plot_status': 'status',
        'park_id': 'park_id',
        'parkid': 'park_id',
        'sector': 'sector',
        'district': 'dist_name',
        'dist_name': 'district',
    }
    
    # Create a case-insensitive mapping
    new_columns = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        
        # Direct match in mapping
        if col_lower in col_mapping:
            new_columns[col] = col_mapping[col_lower]
        # Already normalized
        elif col_lower in ['park_name', 'plot_number', 'rate', 'size_sq_m', 'status', 'sector']:
            new_columns[col] = col_lower
        # Keep original if no mapping
        else:
            new_columns[col] = col
    
    df = df.rename(columns=new_columns)
    
    # Convert columns to lowercase for consistency
    df.columns = [c.lower() if isinstance(c, str) else c for c in df.columns]
    
    return df


def _enrich_plot_record(plot: dict, parks_data: list) -> dict:
    """Enrich plot record with park_name if only park_id is available"""
    if 'park_name' not in plot and 'park_id' in plot:
        # Find park by ID
        for park in parks_data:
            if park.get('_id') == plot.get('park_id'):
                plot['park_name'] = park.get('park_name', 'Unknown')
                break
    
    # Ensure park_name exists
    if 'park_name' not in plot:
        plot['park_name'] = plot.get('park_id', 'Unknown')
    
    return plot


def load_state(state_dir: Path):
    """Load state data with validation and enhanced chunking"""
    state = state_dir.name
    cache["states"][state] = {
        "parks": [],
        "plots": [],
        "pois": [],
        "policy_chunks": []
    }

    logger.info(f"Loading state: {state}")

    # ---- Load Parks & Plots from Excel ----
    for file in state_dir.glob("*.xlsx"):
        logger.info(f"  Loading Excel: {file.name}")
        try:
            xls = pd.ExcelFile(file)
            
            # Load all sheets and check what we have
            sheets_data = {}
            for sheet in xls.sheet_names:
                df = xls.parse(sheet)
                df = _normalize_dataframe_columns(df)
                sheets_data[sheet.lower()] = df
                logger.info(f"    Sheet: {sheet}, Columns: {list(df.columns)[:8]}...")
            
            # First pass: Load parks from sheets with park data
            for sheet_name, df in sheets_data.items():
                if 'park_name' in df.columns or any('park' in c.lower() for c in df.columns):
                    # Check if this looks like a parks sheet (has park_name column)
                    if 'park_name' in df.columns:
                        parks_list = df.to_dict("records")
                        logger.info(f"    Found {len(parks_list)} parks in sheet {sheet_name}")
                        
                        for park in parks_list:
                            # Skip if empty or all NaN
                            if not park or all(pd.isna(v) for v in park.values()):
                                continue
                            
                            # Normalize field names
                            park = normalize_park(park)
                            
                            validation = DataIntegrityValidator.validate_park_data(park)
                            if validation.is_valid or len(validation.errors) == 0:
                                cache["states"][state]["parks"].append(park)
                                logger.debug(f"  Added park: {park.get('park_name', 'Unknown')}")
                            else:
                                logger.debug(f"  Skipping invalid park: {validation.errors}")
            
            # Second pass: Load plots from sheets with plot data
            for sheet_name, df in sheets_data.items():
                if 'plot_number' in df.columns or 'plotno' in df.columns or any('plot' in c.lower() for c in df.columns):
                    # Check if this looks like a plots sheet (has plot_number or plotno column)
                    plot_col = None
                    for col in ['plot_number', 'plotno', 'plot_no']:
                        if col in df.columns:
                            plot_col = col
                            break
                    
                    if plot_col:
                        plots_list = df.to_dict("records")
                        logger.info(f"    Found {len(plots_list)} plots in sheet {sheet_name}")
                        
                        for plot in plots_list:
                            # Skip if empty or all NaN
                            if not plot or all(pd.isna(v) for v in plot.values()):
                                continue
                            
                            # Normalize field names
                            plot = normalize_plot(plot)
                            
                            # Enrich plot with park info if needed
                            plot = _enrich_plot_record(plot, cache["states"][state]["parks"])
                            
                            validation = DataIntegrityValidator.validate_plot_data(plot)
                            if validation.is_valid or len(validation.errors) == 0:
                                cache["states"][state]["plots"].append(plot)
                                logger.debug(f"  Added plot: {plot.get('plot_number', 'Unknown')}")
                            else:
                                logger.debug(f"  Skipping invalid plot: {validation.errors}")
        except Exception as e:
            logger.error(f"Error loading Excel file {file.name}: {e}", exc_info=True)

    # ---- Load POIs from JSON ----
    for file in state_dir.glob("*.json"):
        logger.info(f"  Loading JSON: {file.name}")
        try:
            raw = json.loads(file.read_text())
            feats = raw if isinstance(raw, list) else raw.get("features", [])
            cache["states"][state]["pois"] += feats
        except Exception as e:
            logger.error(f"Error loading JSON file {file.name}: {e}")

    # ---- Load Policies from PDF with Enhanced Chunking ----
    for file in state_dir.glob("*.pdf"):
        logger.info(f"  Loading PDF: {file.name}")
        try:
            with pdfplumber.open(file) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        # Use semantic chunking for better context preservation
                        chunks = create_enhanced_chunks(
                            text=text,
                            source=file.name,
                            page=i + 1,
                            chunk_id_prefix=f"{state}_{file.stem}",
                            chunk_size=800,
                            overlap=200
                        )
                        
                        for chunk in chunks:
                            validation = DataIntegrityValidator.validate_policy_chunk(chunk)
                            if validation.is_valid or len(chunk.get("text", "")) > 50:
                                cache["states"][state]["policy_chunks"].append(chunk)
        except Exception as e:
            logger.error(f"Error loading PDF file {file.name}: {e}")

    logger.info(f"State {state} loaded: "
                f"{len(cache['states'][state]['parks'])} parks, "
                f"{len(cache['states'][state]['plots'])} plots, "
                f"{len(cache['states'][state]['pois'])} POIs, "
                f"{len(cache['states'][state]['policy_chunks'])} policy chunks")


def load_all():
    """Load all state data with validation"""
    logger.info("Starting data load...")
    cache["states"].clear()
    
    for state_dir in BASE.iterdir():
        if state_dir.is_dir():
            try:
                load_state(state_dir)
            except Exception as e:
                logger.error(f"Error loading state {state_dir.name}: {e}")
    
    logger.info(f"Data load complete. Loaded {len(cache['states'])} states")
