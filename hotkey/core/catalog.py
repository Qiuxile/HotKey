"""积木目录：从 catalog.json 加载中文模板、参数和代码模板（不依赖 Qt）。"""

from __future__ import annotations

import json
import re
import string
from dataclasses import dataclass
from pathlib import Path

INDENT = "    "
CATALOG_PATH = Path(__file__).with_name("catalog.json")


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    color: str
    accent: str


@dataclass(frozen=True)
class Param:
    name: str
    placeholder: str = ""
    kind: str = "text"  # text | number
    width: int = 72


@dataclass(frozen=True)
class Snippet:
    id: str
    category: str
    label: str
    code: str
    params: tuple[Param, ...] = ()
    block: bool = False
    slots: tuple[str, ...] = ()
    hidden: bool = False

    # ---------------------------------------------------------------- 渲染

    def param(self, name: str) -> Param | None:
        for param in self.params:
            if param.name == name:
                return param
        return None

    def segments(self) -> list[str | Param]:
        """把中文标签拆成 [文字, 参数, 文字, 参数, ...]，供界面直接铺控件。"""
        result: list[str | Param] = []
        for literal, field, _spec, _conversion in string.Formatter().parse(self.label):
            if literal:
                result.append(literal)
            if field:
                param = self.param(field)
                if param is not None:
                    result.append(param)
        return result

    def blank_values(self) -> dict[str, str]:
        return {param.name: "" for param in self.params}

    def render(self, values: dict[str, str]) -> str:
        return self.label.format(
            **{param.name: values.get(param.name, "") for param in self.params}
        )

    # ---------------------------------------------------------------- 转换

    def code_for_values(self, values: dict[str, str]) -> str:
        """按参数类型转义后生成 Python 代码。"""
        formatted: dict[str, str] = {}
        for param in self.params:
            raw = values.get(param.name, "")
            if param.kind in ("number", "code"):
                formatted[param.name] = str(raw).strip()
            else:
                formatted[param.name] = repr(str(raw))
        return self.code.format(**formatted)

    def parse_text(self, text: str) -> dict[str, str] | None:
        """从中文文本里反解参数（用于旧配置迁移）。"""
        fields = [param.name for param in self.params]
        cleaned = text.strip()

        if not fields:
            return {} if cleaned == self.render({}).strip() else None

        parts: list[str] = []
        for literal, field, _spec, _conversion in string.Formatter().parse(self.label):
            stripped = literal.strip()
            if stripped:
                parts.append(re.escape(stripped))
            if field:
                parts.append(f"(?P<{field}>.*?)")

        match = re.match("^" + "".join(parts) + "$", cleaned, re.DOTALL)
        if not match:
            return None
        return {name: match.group(name).strip() for name in fields}


def _load_catalog(path: Path = CATALOG_PATH) -> tuple[tuple[Category, ...], tuple[Snippet, ...]]:
    data = json.loads(path.read_text(encoding="utf-8"))

    categories = tuple(
        Category(
            id=item["id"],
            label=item["label"],
            color=item.get("color", "#e5e7eb"),
            accent=item.get("accent", "#6b7280"),
        )
        for item in data["categories"]
    )

    snippets: list[Snippet] = []
    for item in data["blocks"]:
        params = tuple(
            Param(
                name=param["name"],
                placeholder=param.get("placeholder", ""),
                kind=param.get("kind", "text"),
                width=int(param.get("width", 72)),
            )
            for param in item.get("params", [])
        )
        snippet = Snippet(
            id=item["id"],
            category=item["category"],
            label=item["label"],
            code=item["code"],
            params=params,
            block=bool(item.get("block", False)),
            slots=tuple(item.get("slots", ())),
            hidden=bool(item.get("hidden", False)),
        )

        fields = [
            name
            for _literal, name, _spec, _conversion in string.Formatter().parse(
                snippet.label
            )
            if name
        ]
        if fields != [param.name for param in params]:
            raise ValueError(
                f"积木 {snippet.id} 的 label 占位符与 params 不一致: {fields}"
            )

        snippets.append(snippet)

    return categories, tuple(snippets)


CATEGORIES, SNIPPETS = _load_catalog()
_BY_ID = {snippet.id: snippet for snippet in SNIPPETS}
_CATEGORY_BY_ID = {category.id: category for category in CATEGORIES}


def snippet(snippet_id: str) -> Snippet:
    return _BY_ID[snippet_id]


def category(category_id: str) -> Category:
    return _CATEGORY_BY_ID[category_id]


def is_container(snippet_id: str) -> bool:
    try:
        return snippet(snippet_id).block
    except KeyError:
        return False


def category_label(category_id: str) -> str:
    try:
        return category(category_id).label
    except KeyError:
        return category_id


def snippets_by_category() -> dict[str, list[Snippet]]:
    grouped: dict[str, list[Snippet]] = {category_.id: [] for category_ in CATEGORIES}
    for snippet_ in SNIPPETS:
        grouped.setdefault(snippet_.category, []).append(snippet_)
    return grouped
