"""Build the Recourse architecture diagrams as one draw.io file, two pages.

Generated rather than hand-drawn, so the geometry can be iterated on and the
shapes stay in step with what the code does.

Two pages on purpose. A single diagram carrying both the layering and the
decision path produced edges spanning the whole canvas, crossing every box
between their ends; the picture was busy without being informative. So:

  1. "How it works" - the whole idea in six big shapes. Someone should be able to
     read it once, at a glance, without following a line back.
  2. "Under the hood" - the same story with the machinery named: the two loops,
     the two interventions, and the duty that fires when the agent is about to do
     nothing.

    python build_architecture.py    ->  recourse-architecture.drawio
"""

from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).parent
OUT = HERE / "recourse-architecture.drawio"

INK, MUTED, LINE, ACCENT = "#161a25", "#5a6273", "#c9cede", "#4429c4"

GROUP = ("rounded=1;whiteSpace=wrap;html=1;fillColor=#f7f8fa;strokeColor=#e3e6ec;"
         "verticalAlign=top;align=left;spacingLeft=14;spacingTop=6;fontSize=12;"
         f"fontStyle=1;fontColor={MUTED};arcSize=4;")
NODE = (f"rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor={LINE};"
        f"fontSize=11;fontColor={INK};arcSize=14;spacing=6;")
ACC = ("rounded=1;whiteSpace=wrap;html=1;fillColor=#efeaff;strokeColor=#4429c4;"
       "fontSize=11;fontColor=#2f1b7a;arcSize=14;spacing=6;")
STOP = ("rounded=1;whiteSpace=wrap;html=1;fillColor=#fdeceb;strokeColor=#b42318;"
        "fontSize=11;fontColor=#912018;arcSize=14;spacing=6;")
OK = ("rounded=1;whiteSpace=wrap;html=1;fillColor=#eefaf3;strokeColor=#12734a;"
      "fontSize=11;fontColor=#0d5c3a;arcSize=14;spacing=6;")
ACTOR = (f"ellipse;whiteSpace=wrap;html=1;fillColor={ACCENT};strokeColor=#2f1b7a;"
         "fontSize=11;fontColor=#ffffff;fontStyle=1;")
NOTE = ("text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fontSize=10;"
        f"fontColor={MUTED};")
TITLE = ("text;html=1;whiteSpace=wrap;align=left;verticalAlign=middle;fontSize=18;"
         f"fontStyle=1;fontColor={INK};")

EDGE = ("edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;jettySize=auto;"
        f"strokeColor={MUTED};fontSize=10;fontColor={MUTED};endArrow=blockThin;"
        "endFill=1;labelBackgroundColor=#ffffff;")
EDGE_ACC = ("edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;jettySize=auto;"
            f"strokeColor={ACCENT};strokeWidth=2;fontSize=10;fontColor={ACCENT};"
            "endArrow=blockThin;endFill=1;labelBackgroundColor=#ffffff;fontStyle=1;")
EDGE_STOP = ("edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;jettySize=auto;"
             "strokeColor=#b42318;fontSize=10;fontColor=#b42318;endArrow=blockThin;"
             "endFill=1;dashed=1;labelBackgroundColor=#ffffff;")


class Page:
    def __init__(self, name: str, w: int, h: int) -> None:
        self.name, self.w, self.h, self.cells = name, w, h, []

    def node(self, ident, label, x, y, w, h, style=NODE):
        # html=1 means the label is markup, so a newline has to be a line break
        # tag - and the tag itself lives inside an XML attribute, so it has to be
        # entity-escaped. Writing a bare <br> made the file invalid XML from the
        # first multi-line label onwards, and draw.io silently rendered only the
        # cells before it.
        value = escape(label).replace("\n", "&lt;br&gt;")
        self.cells.append(
            f'<mxCell id="{ident}" value="{value}" style="{style}" vertex="1" '
            f'parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" '
            'as="geometry"/></mxCell>'
        )

    def edge(self, ident, src, dst, label="", style=EDGE, exit=None, entry=None):
        s = style
        if exit:
            s += f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;"
        if entry:
            s += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
        self.cells.append(
            f'<mxCell id="{ident}" value="{escape(label)}" style="{s}" edge="1" '
            f'parent="1" source="{src}" target="{dst}">'
            '<mxGeometry relative="1" as="geometry"/></mxCell>'
        )

    def xml(self, ident):
        return (
            f'  <diagram id="{ident}" name="{escape(self.name)}">\n'
            f'    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" '
            f'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            f'pageWidth="{self.w}" pageHeight="{self.h}" math="0" shadow="0">\n'
            '      <root>\n        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n'
            + "\n".join("        " + c for c in self.cells) + "\n"
            '      </root>\n    </mxGraphModel>\n  </diagram>\n'
        )


# ============================ page 1: how it works ==========================
# Six boxes and one line of text under each. The third branch is the point of the
# whole thing and has to be legible without reading a caption.

BIG = ("rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#c9cede;"
       "fontSize=17;fontColor=#161a25;arcSize=10;spacing=12;")
BIG_ACC = ("rounded=1;whiteSpace=wrap;html=1;fillColor=#efeaff;strokeColor=#4429c4;"
           "strokeWidth=2;fontSize=17;fontColor=#2f1b7a;arcSize=10;spacing=12;")
BIG_OK = ("rounded=1;whiteSpace=wrap;html=1;fillColor=#eefaf3;strokeColor=#12734a;"
          "strokeWidth=2;fontSize=17;fontColor=#0d5c3a;arcSize=10;spacing=12;")
BIG_ACTOR = ("ellipse;whiteSpace=wrap;html=1;fillColor=#4429c4;strokeColor=#2f1b7a;"
             "fontSize=17;fontColor=#ffffff;fontStyle=1;")
FOOT = ("text;html=1;whiteSpace=wrap;align=left;verticalAlign=middle;fontSize=13;"
        "fontColor=#5a6273;")
BIG_EDGE = ("edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#5a6273;"
            "strokeWidth=2;fontSize=14;fontColor=#5a6273;endArrow=blockThin;endFill=1;"
            "labelBackgroundColor=#ffffff;")
BIG_EDGE_ACC = ("edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#4429c4;"
                "strokeWidth=2;fontSize=14;fontColor=#4429c4;fontStyle=1;"
                "endArrow=blockThin;endFill=1;labelBackgroundColor=#ffffff;")

a = Page("How it works", 1240, 560)
a.node("t", "Recourse", 50, 34, 300, 34, TITLE)

a.node("s1", "A claim is\ndenied", 50, 180, 160, 100, BIG_ACTOR)
a.node("s2", "Recourse reads the\ndenial's own code", 270, 175, 210, 110, BIG)
a.node("s3", "Paperwork,\nor medicine?", 540, 185, 180, 90, BIG_ACC)

a.node("o1", "Paperwork — it drafts\nthe appeal for you", 780, 90, 300, 80, BIG_OK)
a.node("o2", "Medicine — only your\ndoctor can argue this", 780, 190, 300, 80, BIG_ACC)
a.node("o3", "And it counts every\ndeadline, all the way down", 780, 290, 300, 80, BIG)

a.node("f", "You have 180 days to appeal. The plan owes you an answer in 30 or 60. "
            "Nobody else is counting.", 50, 420, 1060, 26, FOOT)
a.node("f2", "It drafts. It never files, and it never goes quiet as a window closes.",
       50, 448, 1060, 26, FOOT)

a.edge("a1", "s1", "s2", "", BIG_EDGE)
a.edge("a2", "s2", "s3", "", BIG_EDGE)
a.edge("a3", "s3", "o1", "", BIG_EDGE_ACC, exit=(1, 0.2), entry=(0, 0.5))
a.edge("a4", "s3", "o2", "", BIG_EDGE_ACC, exit=(1, 0.5), entry=(0, 0.5))
a.edge("a5", "s3", "o3", "", BIG_EDGE, exit=(1, 0.8), entry=(0, 0.5))

# ========================= page 2 placeholder ==============================
XML = ('<mxfile host="app.diagrams.net" type="device">\n' + a.xml("how-it-works")
       + '</mxfile>\n')
OUT.write_text(XML, encoding="utf-8")
print(f"wrote {OUT}  ({len(a.cells)} cells)")
