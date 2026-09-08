"""Interactive terminal triage workflow for Word document remediation."""
import re
from pathlib import Path
from typing import Any, Callable, Optional
from docx import Document
from .audit import audit_file


def _set_image_alt_text(doc: Any, location: str, alt_text: str):
    # Location format usually 'paragraph[i].run[j]' or similar
    # Find all inline shapes or drawings
    for p in doc.paragraphs:
        for r in p.runs:
            for child in r._r:
                if child.tag.endswith("drawing"):
                    for cNvPr in child.iter():
                        if cNvPr.tag.endswith("cNvPr") or cNvPr.tag.endswith("docPr"):
                            cNvPr.set("descr", alt_text)
                            return


def _mark_image_decorative(doc: Any, location: str):
    for p in doc.paragraphs:
        for r in p.runs:
            for child in r._r:
                if child.tag.endswith("drawing"):
                    for cNvPr in child.iter():
                        if cNvPr.tag.endswith("cNvPr") or cNvPr.tag.endswith("docPr"):
                            cNvPr.set("descr", "")
                            return


def _set_doc_title(doc: Any, title_text: str):
    doc.core_properties.title = title_text


def run_interactive_triage(
    in_path: str | Path,
    out_path: Optional[str | Path] = None,
    input_func: Optional[Callable[[str], str]] = None,
    print_func: Optional[Callable[..., None]] = None,
) -> int:
    """Walk user interactively through author-intent accessibility barriers."""
    if input_func is None:
        input_func = input
    if print_func is None:
        print_func = print

    in_p = Path(in_path)
    out_p = Path(out_path) if out_path else in_p.parent / f"{in_p.stem}-triaged.docx"

    doc = Document(str(in_p))
    res = audit_file(in_p)
    findings = res.get("findings", [])

    items_triaged = 0
    print_func(f"\n=== docx-a11y Interactive Accessibility Triage: {in_p.name} ===\n")

    for f in findings:
        rule_id = f.get("rule_id", "")
        location = f.get("location", "")
        desc = f.get("description", "")

        if rule_id in ("image-alt-missing", "graphic-missing-alt"):
            print_func("\n[Visual Asset Lacks Alternative Text]")
            print_func(f"Location: {location}")
            print_func(f"Issue:    {desc}")
            ans = input_func("Enter alt text description (or 'd' for decorative, 's' to skip): ").strip()
            if ans.lower() == "s" or not ans:
                continue
            elif ans.lower() == "d":
                _mark_image_decorative(doc, location)
                items_triaged += 1
                print_func("-> Marked shape as decorative.")
            else:
                _set_image_alt_text(doc, location, ans)
                items_triaged += 1
                print_func(f"-> Set alt text: '{ans}'")

        elif rule_id in ("title-missing", "doc-title-missing"):
            print_func("\n[Document Missing Title]")
            print_func(f"Location: {location}")
            ans = input_func("Enter a title for this document (or 's' to skip): ").strip()
            if ans.lower() != "s" and ans:
                _set_doc_title(doc, ans)
                items_triaged += 1
                print_func(f"-> Added document title: '{ans}'")

    doc.save(str(out_p))
    print_func(f"\nTriage complete! {items_triaged} items updated. Saved to: {out_p}\n")
    return items_triaged
