from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from browser_use.dom.history_tree_processor.service import DOMHistoryElement
from browser_use.dom.views import DOMState


# Pydantic
class TabInfo(BaseModel):
	"""Represents information about a browser tab"""

	page_id: int
	url: str
	title: str
	parent_page_id: int | None = None  # parent page that contains this popup or cross-origin iframe


class GroupTabsAction(BaseModel):
	tab_ids: list[int]
	title: str
	color: str | None = 'blue'


class UngroupTabsAction(BaseModel):
	tab_ids: list[int]


@dataclass
class BrowserState(DOMState):
	url: str
	title: str
	tabs: list[TabInfo]
	screenshot: str | None = None
	pixels_above: int = 0
	pixels_below: int = 0
	browser_errors: list[str] = field(default_factory=list)


@dataclass
class BrowserStateHistory:
	url: str
	title: str
	tabs: list[TabInfo]
	interacted_element: list[DOMHistoryElement | None] | list[None]
	screenshot: str | None = None

	def to_dict(self) -> dict[str, Any]:
		data = {}
		data['tabs'] = [tab.model_dump() for tab in self.tabs]
		data['screenshot'] = self.screenshot
		data['interacted_element'] = [el.to_dict() if el else None for el in self.interacted_element]
		data['url'] = self.url
		data['title'] = self.title
		return data


class BrowserError(Exception):
	"""Base class for all browser errors"""


class URLNotAllowedError(BrowserError):
	"""Error raised when a URL is not allowed"""
