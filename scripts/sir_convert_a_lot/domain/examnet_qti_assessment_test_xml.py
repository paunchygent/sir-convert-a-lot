"""QTI 2.1 assessmentTest serialization for Exam.net-oriented packages.

Purpose:
    Serialize the package-level assessmentTest that wires every generated
    assessment item into one linear test part, matching the empirically
    confirmed Exam.net import skeleton.

Relationships:
    - Used by `domain.examnet_qti_package` when planning package files.
    - Shares the QTI 2.1 namespace constants with `domain.examnet_qti_xml`.
"""

from __future__ import annotations

from xml.etree import ElementTree

from scripts.sir_convert_a_lot.domain.examnet_qti_xml import (
    QTI_NAMESPACE,
    QTI_SCHEMA_LOCATION,
    XSI_NAMESPACE,
)

EXAMNET_QTI_ASSESSMENT_TEST_PATH = "assessment.xml"
EXAMNET_QTI_TEST_RESOURCE_IDENTIFIER = "res_test"
EXAMNET_QTI_TEST_RESOURCE_TYPE = "imsqti_test_xmlv2p1"


def serialize_qti_assessment_test(
    *,
    package_name: str,
    item_ids: tuple[str, ...],
) -> bytes:
    """Serialize the package assessmentTest to UTF-8 XML bytes."""

    ElementTree.register_namespace("", QTI_NAMESPACE)
    ElementTree.register_namespace("xsi", XSI_NAMESPACE)
    root = ElementTree.Element(
        _qti("assessmentTest"),
        {
            "identifier": "examnet_qti_test",
            "title": package_name,
            _xsi("schemaLocation"): QTI_SCHEMA_LOCATION,
        },
    )
    part = ElementTree.SubElement(
        root,
        _qti("testPart"),
        {
            "identifier": "part_001",
            "navigationMode": "linear",
            "submissionMode": "individual",
        },
    )
    section = ElementTree.SubElement(
        part,
        _qti("assessmentSection"),
        {
            "identifier": "section_001",
            "title": package_name,
            "visible": "true",
        },
    )
    for item_id in item_ids:
        ElementTree.SubElement(
            section,
            _qti("assessmentItemRef"),
            {
                "identifier": f"ref_{item_id}",
                "href": f"items/{item_id}.xml",
                "fixed": "false",
            },
        )
    ElementTree.indent(root, space="  ")
    xml_text = ElementTree.tostring(
        root,
        encoding="unicode",
        xml_declaration=False,
        short_empty_elements=True,
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_text}\n'.encode("utf-8")


def _qti(local_name: str) -> str:
    return f"{{{QTI_NAMESPACE}}}{local_name}"


def _xsi(local_name: str) -> str:
    return f"{{{XSI_NAMESPACE}}}{local_name}"
