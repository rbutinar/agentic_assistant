from browser_use.dom.views import DOMElementNode
from browser_use.utils.dom_utils import DOMUtils


class ClickableElementProcessor:
	@staticmethod
	def get_clickable_elements_hashes(dom_element: DOMElementNode) -> set[str]:
		"""Get all clickable elements in the DOM tree"""
		return DOMUtils.get_clickable_elements_hashes(dom_element)

	@staticmethod
	def get_clickable_elements(dom_element: DOMElementNode) -> list[DOMElementNode]:
		"""Get all clickable elements in the DOM tree"""
		return DOMUtils.get_clickable_elements(dom_element)

	@staticmethod
	def hash_dom_element(dom_element: DOMElementNode) -> str:
		"""Hash a DOM element using consolidated utilities."""
		return DOMUtils.hash_dom_element(dom_element)

