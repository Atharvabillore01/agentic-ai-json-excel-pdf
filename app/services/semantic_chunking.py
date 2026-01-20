"""
Advanced semantic-aware chunking for better context preservation.
"""
from typing import List, Dict, Any, Optional
import re
import logging

logger = logging.getLogger(__name__)


class ChunkMetadata:
    """Metadata for a chunk"""
    def __init__(
        self,
        chunk_id: str,
        source: str,
        page: int,
        section: Optional[str] = None,
        subsection: Optional[str] = None,
        heading: Optional[str] = None,
        is_list: bool = False,
        is_table: bool = False,
        parent_chunk_id: Optional[str] = None,
        char_start: int = 0,
        char_end: int = 0,
    ):
        self.chunk_id = chunk_id
        self.source = source
        self.page = page
        self.section = section
        self.subsection = subsection
        self.heading = heading
        self.is_list = is_list
        self.is_table = is_table
        self.parent_chunk_id = parent_chunk_id
        self.char_start = char_start
        self.char_end = char_end
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "page": self.page,
            "section": self.section,
            "subsection": self.subsection,
            "heading": self.heading,
            "is_list": self.is_list,
            "is_table": self.is_table,
            "parent_chunk_id": self.parent_chunk_id,
            "char_start": self.char_start,
            "char_end": self.char_end,
        }


class SemanticChunker:
    """
    Advanced chunking that preserves semantic structure.
    Handles sections, lists, tables, and maintains context.
    """
    
    def __init__(
        self,
        chunk_size: int = 800,
        overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_text(
        self,
        text: str,
        source: str,
        page: int,
        chunk_id_prefix: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Intelligently chunk text while preserving semantic structure.
        
        Args:
            text: Full text to chunk
            source: Source document name
            page: Page number
            chunk_id_prefix: Prefix for chunk IDs
        
        Returns:
            List of chunk dictionaries with metadata
        """
        if not text or len(text.strip()) == 0:
            return []
        
        # Step 1: Extract structural elements
        sections = self._extract_sections(text)
        
        # Step 2: Create chunks respecting structure
        chunks = []
        chunk_counter = 0
        
        for section_info in sections:
            section_text = section_info["text"]
            section_name = section_info["section"]
            subsection_name = section_info.get("subsection")
            heading = section_info.get("heading")
            
            # Chunk the section content
            section_chunks = self._create_chunks_for_section(
                section_text,
                source,
                page,
                chunk_id_prefix,
                chunk_counter,
                section_name,
                subsection_name,
                heading,
            )
            
            chunks.extend(section_chunks)
            chunk_counter += len(section_chunks)
        
        return chunks
    
    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """Extract sections, subsections, and structural elements"""
        lines = text.split("\n")
        sections = []
        current_section = None
        current_subsection = None
        current_heading = None
        current_content = []
        
        for line in lines:
            stripped = line.strip()
            
            # Detect section headers (usually all caps or numbered)
            if self._is_section_header(stripped):
                # Save previous section
                if current_content:
                    sections.append(self._build_section_dict(
                        current_section,
                        current_subsection,
                        current_heading,
                        "\n".join(current_content)
                    ))
                    current_content = []
                
                current_section = stripped
                current_subsection = None
                current_heading = None
            
            # Detect subsection headers
            elif self._is_subsection_header(stripped):
                # Save current subsection
                if current_content:
                    sections.append(self._build_section_dict(
                        current_section,
                        current_subsection,
                        current_heading,
                        "\n".join(current_content)
                    ))
                    current_content = []
                
                current_subsection = stripped
                current_heading = None
            
            # Detect headings
            elif self._is_heading(stripped) and stripped:
                # Save previous
                if current_content:
                    sections.append(self._build_section_dict(
                        current_section,
                        current_subsection,
                        current_heading,
                        "\n".join(current_content)
                    ))
                    current_content = []
                
                current_heading = stripped
            
            # Content line
            else:
                if stripped:  # Skip empty lines
                    current_content.append(line)
        
        # Save last section
        if current_content:
            sections.append(self._build_section_dict(
                current_section,
                current_subsection,
                current_heading,
                "\n".join(current_content)
            ))
        
        # If no structural elements found, return whole text as one section
        if not sections:
            sections = [{"text": text, "section": "content"}]
        
        return sections
    
    def _build_section_dict(
        self,
        section: Optional[str],
        subsection: Optional[str],
        heading: Optional[str],
        content: str,
    ) -> Dict[str, Any]:
        """Build section dictionary"""
        return {
            "text": content,
            "section": section or "content",
            "subsection": subsection,
            "heading": heading,
        }
    
    def _create_chunks_for_section(
        self,
        section_text: str,
        source: str,
        page: int,
        chunk_id_prefix: str,
        chunk_counter: int,
        section_name: str,
        subsection_name: Optional[str],
        heading: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Create chunks for a single section"""
        chunks = []
        
        if len(section_text) <= self.chunk_size:
            # Small enough for single chunk
            chunk_id = f"{chunk_id_prefix}_chunk_{chunk_counter}"
            chunks.append({
                "id": chunk_id,
                "text": section_text.strip(),
                "source": source,
                "page": page,
                "section": section_name,
                "subsection": subsection_name,
                "heading": heading,
                "is_list": self._is_list_content(section_text),
                "is_table": self._is_table_content(section_text),
                "metadata": ChunkMetadata(
                    chunk_id=chunk_id,
                    source=source,
                    page=page,
                    section=section_name,
                    subsection=subsection_name,
                    heading=heading,
                    is_list=self._is_list_content(section_text),
                    is_table=self._is_table_content(section_text),
                    char_start=0,
                    char_end=len(section_text),
                ).to_dict()
            })
        else:
            # Need to split into multiple chunks with overlap
            sentences = self._split_into_sentences(section_text)
            current_chunk = []
            current_length = 0
            char_pos = 0
            
            for sentence in sentences:
                sentence_len = len(sentence)
                
                if current_length + sentence_len > self.chunk_size and current_chunk:
                    # Save current chunk
                    chunk_text = " ".join(current_chunk).strip()
                    if len(chunk_text) >= self.min_chunk_size:
                        chunk_id = f"{chunk_id_prefix}_chunk_{chunk_counter}"
                        chunks.append({
                            "id": chunk_id,
                            "text": chunk_text,
                            "source": source,
                            "page": page,
                            "section": section_name,
                            "subsection": subsection_name,
                            "heading": heading,
                            "is_list": self._is_list_content(chunk_text),
                            "is_table": self._is_table_content(chunk_text),
                            "metadata": ChunkMetadata(
                                chunk_id=chunk_id,
                                source=source,
                                page=page,
                                section=section_name,
                                subsection=subsection_name,
                                heading=heading,
                                is_list=self._is_list_content(chunk_text),
                                is_table=self._is_table_content(chunk_text),
                                char_start=char_pos - current_length,
                                char_end=char_pos,
                            ).to_dict()
                        })
                        chunk_counter += 1
                    
                    # Create overlap
                    overlap_sentences = []
                    overlap_len = 0
                    for sent in reversed(current_chunk):
                        if overlap_len + len(sent) > self.overlap:
                            break
                        overlap_sentences.insert(0, sent)
                        overlap_len += len(sent)
                    
                    current_chunk = overlap_sentences
                    current_length = overlap_len
                
                current_chunk.append(sentence)
                current_length += sentence_len
                char_pos += sentence_len
            
            # Save final chunk
            if current_chunk:
                chunk_text = " ".join(current_chunk).strip()
                if len(chunk_text) >= self.min_chunk_size:
                    chunk_id = f"{chunk_id_prefix}_chunk_{chunk_counter}"
                    chunks.append({
                        "id": chunk_id,
                        "text": chunk_text,
                        "source": source,
                        "page": page,
                        "section": section_name,
                        "subsection": subsection_name,
                        "heading": heading,
                        "is_list": self._is_list_content(chunk_text),
                        "is_table": self._is_table_content(chunk_text),
                        "metadata": ChunkMetadata(
                            chunk_id=chunk_id,
                            source=source,
                            page=page,
                            section=section_name,
                            subsection=subsection_name,
                            heading=heading,
                            is_list=self._is_list_content(chunk_text),
                            is_table=self._is_table_content(chunk_text),
                            char_start=char_pos - current_length,
                            char_end=char_pos,
                        ).to_dict()
                    })
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences intelligently"""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _is_section_header(self, text: str) -> bool:
        """Detect section headers"""
        if not text:
            return False
        # All caps or starts with number
        return (text.isupper() and len(text) > 3) or re.match(r'^\d+\.?\s+', text)
    
    def _is_subsection_header(self, text: str) -> bool:
        """Detect subsection headers"""
        if not text:
            return False
        return re.match(r'^(\d+\.\d+|\s{2,}[-•*]|\s{2,}[A-Z])', text) is not None
    
    def _is_heading(self, text: str) -> bool:
        """Detect regular headings"""
        if not text:
            return False
        return len(text) < 100 and (
            text[0].isupper() or 
            re.match(r'^[A-Z][a-z\s]+:', text) is not None
        )
    
    def _is_list_content(self, text: str) -> bool:
        """Detect if content is a list"""
        lines = text.split("\n")
        list_markers = 0
        for line in lines:
            if re.match(r'^\s*[-•*]\s', line) or re.match(r'^\s*\d+\.\s', line):
                list_markers += 1
        
        return list_markers > len(lines) * 0.3 if lines else False
    
    def _is_table_content(self, text: str) -> bool:
        """Detect if content is a table"""
        lines = text.split("\n")
        pipe_count = sum(1 for line in lines if "|" in line)
        return pipe_count > len(lines) * 0.5 if lines else False


def create_enhanced_chunks(
    text: str,
    source: str,
    page: int,
    chunk_id_prefix: str = "chunk",
    chunk_size: int = 800,
    overlap: int = 200,
) -> List[Dict[str, Any]]:
    """
    Convenience function to create enhanced chunks with all metadata.
    
    Args:
        text: Text to chunk
        source: Source document
        page: Page number
        chunk_id_prefix: Prefix for chunk IDs
        chunk_size: Target chunk size in characters
        overlap: Overlap between chunks in characters
    
    Returns:
        List of enhanced chunks with metadata
    """
    chunker = SemanticChunker(chunk_size=chunk_size, overlap=overlap)
    return chunker.chunk_text(text, source, page, chunk_id_prefix)
