"""Repair pagination on a copy of the author's final Word report.

Preserves text, eight table matrices, image assets, body typography and margins.
No experiment, score, prompt or runtime is changed.
"""

import argparse
import re
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


def matrices(document):
    return [[[cell.text for cell in row.cells] for row in table.rows] for table in document.tables]


def media(path):
    with ZipFile(path) as archive:
        return {name: sha256(archive.read(name)).hexdigest() for name in archive.namelist() if name.startswith("word/media/")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path)
    parser.add_argument("output",type=Path)
    args = parser.parse_args()
    assert args.source.resolve() != args.output.resolve()
    original = Document(args.source)
    document = Document(args.source)
    assert len(document.tables) == 8
    for index, table in enumerate(document.tables):
        columns = len(table.columns)
        if columns == 6:
            widths = [1.10, .90, .78, 1.02, 1.02, 1.18]
        elif columns == 3:
            widths = [1.20, 2.40, 2.40]
        elif columns == 4 and index != 4:
            widths = [2.40, 1.20, 1.20, 1.20]
        else:
            widths = None
        if widths:
            table.autofit = False
            for grid, width in zip(table._tbl.tblGrid.gridCol_lst,widths):
                grid.set(qn("w:w"),str(round(width*1440)))
        for row_number,row in enumerate(table.rows):
            if row._tr.trPr is None or row._tr.trPr.find(qn("w:cantSplit")) is None:
                row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
            for column,cell in enumerate(row.cells):
                if widths:
                    cell.width = Inches(widths[column])
                for paragraph in cell.paragraphs:
                    if index != 0:
                        paragraph.paragraph_format.keep_with_next = row_number < len(table.rows)-1
                    if columns == 6:
                        for run in paragraph.runs:
                            run.font.size = Pt(9.5)
        previous = table._tbl.getprevious()
        if index != 0 and previous is not None and previous.tag == qn("w:p"):
            props = previous.find(qn("w:pPr"))
            if props is None:
                props = OxmlElement("w:pPr");previous.insert(0,props)
            if props.find(qn("w:keepNext")) is None:
                props.append(OxmlElement("w:keepNext"))
    in_prompt = False
    for paragraph in document.paragraphs:
        if paragraph._p.xpath(".//w:drawing|.//w:pict"):
            paragraph.paragraph_format.keep_with_next = True
        if paragraph.text.startswith("Figure "):
            paragraph.paragraph_format.keep_together = True
            paragraph.paragraph_format.keep_with_next = False
        if re.match(r"^(?:[1-9](?:\.[1-9])? |Appendix [AB] |References and Evidence)",paragraph.text):
            paragraph.paragraph_format.keep_with_next = True
        if paragraph.text.startswith("The following text is reviewer-v1"):
            paragraph.paragraph_format.keep_with_next = True
        if paragraph.text.startswith("You are an approval reviewer"):
            in_prompt = True
        if in_prompt:
            paragraph.paragraph_format.keep_together = True
            paragraph.paragraph_format.keep_with_next = not paragraph.text.startswith("The reason must be nonempty")
            if paragraph.text.startswith("The reason must be nonempty"):
                in_prompt = False
    # Keep the review-load plot beside its discussion without changing pixels.
    shape = document.inline_shapes[1]
    scale = Inches(5.2) / shape.width
    shape.height = round(shape.height * scale)
    shape.width = Inches(5.2)
    # The author's final empty paragraph must not generate a blank last page.
    if not document.paragraphs[-1].text.strip():
        tail = document.paragraphs[-1]
        tail.paragraph_format.space_before = Pt(0)
        tail.paragraph_format.space_after = Pt(0)
        tail.paragraph_format.line_spacing = Pt(1)
        tail.paragraph_format.keep_with_next = False
        for run in tail.runs:
            run.font.size = Pt(1)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    document.save(args.output)
    saved=Document(args.output)
    assert [p.text for p in original.paragraphs] == [p.text for p in saved.paragraphs]
    assert matrices(original)==matrices(saved)
    assert media(args.source)==media(args.output)
    print("Verified unchanged paragraphs, all8 tables, and all embedded images.")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
