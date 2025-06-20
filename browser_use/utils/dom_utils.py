"""
Consolidated DOM utilities to eliminate code duplication.
"""
import hashlib
from typing import Dict, List, Any

from browser_use.dom.views import DOMElementNode


class DOMUtils:
    """Consolidated utilities for DOM operations."""
    
    @staticmethod
    def hash_dom_element(dom_element: DOMElementNode) -> str:
        """Create a hash for a DOM element using consistent criteria."""
        parent_branch_path = DOMUtils._get_parent_branch_path(dom_element)
        branch_path_hash = DOMUtils._parent_branch_path_hash(parent_branch_path)
        attributes_hash = DOMUtils._attributes_hash(dom_element.attributes)
        xpath_hash = DOMUtils._xpath_hash(dom_element.xpath)
        
        return DOMUtils._hash_string(f'{branch_path_hash}-{attributes_hash}-{xpath_hash}')
    
    @staticmethod
    def get_clickable_elements(dom_element: DOMElementNode) -> List[DOMElementNode]:
        """Get all clickable elements in the DOM tree."""
        clickable_elements = []
        for child in dom_element.children:
            if isinstance(child, DOMElementNode):
                if child.highlight_index:
                    clickable_elements.append(child)
                clickable_elements.extend(DOMUtils.get_clickable_elements(child))
        return clickable_elements
    
    @staticmethod
    def get_clickable_elements_hashes(dom_element: DOMElementNode) -> set[str]:
        """Get hashes of all clickable elements in the DOM tree."""
        clickable_elements = DOMUtils.get_clickable_elements(dom_element)
        return {DOMUtils.hash_dom_element(element) for element in clickable_elements}
    
    @staticmethod
    def _get_parent_branch_path(dom_element: DOMElementNode) -> List[str]:
        """Get the parent branch path for a DOM element."""
        parents: List[DOMElementNode] = []
        current_element: DOMElementNode = dom_element
        
        while current_element.parent is not None:
            parents.append(current_element)
            current_element = current_element.parent
        
        parents.reverse()
        return [parent.tag_name for parent in parents]
    
    @staticmethod
    def _parent_branch_path_hash(parent_branch_path: List[str]) -> str:
        """Hash the parent branch path."""
        parent_branch_path_string = '/'.join(parent_branch_path)
        return hashlib.sha256(parent_branch_path_string.encode()).hexdigest()
    
    @staticmethod
    def _attributes_hash(attributes: Dict[str, str]) -> str:
        """Hash the attributes dictionary."""
        attributes_string = ''.join(f'{key}={value}' for key, value in attributes.items())
        return DOMUtils._hash_string(attributes_string)
    
    @staticmethod
    def _xpath_hash(xpath: str) -> str:
        """Hash the xpath string."""
        return DOMUtils._hash_string(xpath)
    
    @staticmethod
    def _text_hash(dom_element: DOMElementNode) -> str:
        """Hash the text content of a DOM element."""
        text_string = dom_element.get_all_text_till_next_clickable_element()
        return DOMUtils._hash_string(text_string)
    
    @staticmethod
    def _hash_string(string: str) -> str:
        """Create SHA256 hash of a string."""
        return hashlib.sha256(string.encode()).hexdigest() 