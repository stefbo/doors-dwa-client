# printers.py
"""
Utility helpers for presenting DWA structures.

The classes here are deliberately **stateless** so that the core domain
objects stay lean and test-focused.
"""

from __future__ import annotations

from typing import Union

from dwa_client.resources import Folder, RemoteResource, Project, Document


class FolderTreePrinter:
    """
    Recursively pretty-prints a Folder hierarchy.

    Parameters
    ----------
    show_objects :
        If ``True`` requirement objects (modules’ rows) are printed as
        leaves; otherwise only Folder / Module nodes are shown.
    bullet_folders :
        Character to use for folders/modules (default ``"•"``).
    bullet_objects :
        Character to use for objects (default ``"-"``).
    indent_unit :
        String prepended per depth level (default two spaces).
    """

    def __init__(
        self,
        *,
        show_objects: bool = False,
        bullet_folders: str = "•",
        bullet_objects: str = "-",
        indent_unit: str = "  ",
    ) -> None:
        self.show_objects = show_objects
        self.bullet_folders = bullet_folders
        self.bullet_objects = bullet_objects
        self.indent_unit = indent_unit

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def print_tree(self, folder: Folder) -> None:
        """Print the full subtree rooted at *folder*."""
        self._print_node(folder, depth=0)

    # ------------------------------------------------------------------
    # implementation helpers
    # ------------------------------------------------------------------
    def _print_node(self, node: RemoteResource, depth: int) -> None:
        indent = self.indent_unit * depth
        if isinstance(node, Project):
            print(f"{indent}{self.bullet_folders} [PROJECT] {node.name} [{node.guid}]")
        elif isinstance(node, Document):
            print(f"{indent}{self.bullet_folders} [DOCUMENT] {node.name} [{node.guid}]")
        elif isinstance(node, Folder):
            print(f"{indent}{self.bullet_folders} {node.name} [{node.guid}]")
        else:  # shouldn’t happen – root must be Folder
            self._print_leaf(node, depth)
        if isinstance(node, Folder):
            for child in node.get_children():
                if isinstance(child, Folder):
                    self._print_node(child, depth + 1)
                elif self.show_objects:
                    self._print_leaf(child, depth + 1)

    def _print_leaf(self, node: RemoteResource, depth: int) -> None:
        indent = self.indent_unit * depth
        print(f"{indent}{self.bullet_objects} {node.name} [{node.guid}]")
        indent = self.indent_unit * depth
        print(f"{indent}{self.bullet_objects} {node.name} [{node.guid}]")
