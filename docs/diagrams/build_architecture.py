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

# ========================== page 2: under the hood ==========================
# One denial, end to end. Three columns, because the story has three parts that do
# not interleave: what WATCH decides, what happens to a guarded tool call, and the
# duty that fires on a schedule while all of that is idle.
#
# The two interventions are drawn in their real order. `CitationGuard` sits above
# `EscalationPolicy` because its Deny short-circuits: an unsupported clinical claim
# must never reach a policy that would weigh it on urgency and find nothing wrong.

b = Page("Under the hood", 2420, 1120)
b.node("t", "One denied line, end to end", 50, 30, 700, 34, TITLE)
b.node("t2", "The two interventions in the order they run, and the duty that fires "
             "when the agent is about to do nothing.", 50, 68, 900, 22, NOTE)

# -- what WATCH decides ------------------------------------------------------
b.node("w1", "A denied line\narrives", 60, 195, 170, 90, ACTOR)
b.node("w2", "WATCH loop\nreads the EOB and classifies each denial\nfrom the X12 code "
             "the denial itself carries", 270, 180, 280, 120)
# One classification with three mutually exclusive outcomes, so all three hang off
# the same spine. Chaining them vertically drew clerical *into* clinical *into*
# unassessable, which says the denial passes through all three in turn.
b.node("w3", "clerical\nRecourse may prepare this one alone", 330, 360, 280, 70, ACC)
b.node("w4", "clinical\nhanded straight back — no combination of\ndocuments makes it "
             "yours", 330, 450, 280, 90, STOP)
b.node("w5", "unassessable\na code it cannot read is never “fine”", 330, 560,
       280, 80)
b.edge("wa", "w1", "w2")
b.edge("wb", "w2", "w3", "", EDGE_ACC, exit=(0.10, 1), entry=(0, 0.5))
b.edge("wc", "w2", "w4", "", EDGE_STOP, exit=(0.20, 1), entry=(0, 0.5))
b.edge("wd", "w2", "w5", "", EDGE, exit=(0.30, 1), entry=(0, 0.5))

# -- the guarded tool call ---------------------------------------------------
b.node("m0", "proposes\ndraft_appeal", 640, 360, 190, 70, ACC)
b.node("m1", "1 · CitationGuard\ndoes every clinical sentence cite a\ndocument in "
             "this case file?", 900, 165, 300, 115)
b.node("m1x", "Deny\nnever reaches the world. There is nothing\nhere for a person to "
              "approve.", 1290, 170, 300, 105, STOP)
b.node("m2", "2 · EscalationPolicy\nmay it act alone at this\nautonomy level?",
       900, 340, 300, 110, ACC)
b.node("m2x", "Proceed\nwithin limits", 1290, 350, 220, 80, OK)
b.node("m3", "Commit + journal entry\nwhat it wrote · what it cited · who "
             "decided", 1620, 340, 280, 110, OK)
b.node("m4", "Confirm\nsnapshot the run and stop", 900, 510, 300, 85, ACC)
b.node("m5", "Decision inbox\nthe question, and the whole agent state", 900, 650,
       300, 95)
b.node("m6", "You", 960, 800, 180, 80, ACTOR)
b.node("m7", "Approve\nthe same run resumes, later,\non another machine", 1290, 790,
       300, 100, OK)
b.node("m8", "Decline\nnothing changes, and it is written\ndown that you refused",
       1290, 930, 300, 100, STOP)

b.edge("ma", "w3", "m0", "", EDGE_ACC, exit=(1, 0.5), entry=(0, 0.5))
b.edge("mb", "m0", "m1", "", EDGE_ACC, exit=(1, 0.5), entry=(0, 0.5))
b.edge("mc", "m1", "m1x", "Deny", EDGE_STOP, exit=(1, 0.5), entry=(0, 0.5))
b.edge("md", "m1", "m2", "Proceed", EDGE, exit=(0.5, 1), entry=(0.5, 0))
b.edge("me", "m2", "m2x", "no rule fires", EDGE, exit=(1, 0.5), entry=(0, 0.5))
b.edge("mf", "m2x", "m3", "", EDGE, exit=(1, 0.5), entry=(0, 0.5))
b.edge("mg", "m2", "m4", "a rule fires", EDGE_ACC, exit=(0.5, 1), entry=(0.5, 0))
b.edge("mh", "m4", "m5", "", EDGE_ACC, exit=(0.5, 1), entry=(0.5, 0))
b.edge("mi", "m5", "m6", "surfaced on Decisions", EDGE, exit=(0.5, 1), entry=(0.5, 0))
b.edge("mj", "m6", "m7", "", EDGE_ACC, exit=(1, 0.5), entry=(0, 0.5))
b.edge("mk", "m6", "m8", "", EDGE_STOP, exit=(0.5, 1), entry=(0, 0.5))
b.edge("ml", "m7", "m3", "resumes the same run", EDGE_ACC, exit=(0.5, 0), entry=(0.5, 1))

# -- the duty ----------------------------------------------------------------
# PRESS is not reachable by an edge from the tool call, and that is the point: it
# runs whether or not the agent is doing anything. Drawing an arrow into it from
# the middle column would say the opposite.
b.node("p1", "PRESS loop\nruns on a schedule, not on a tool call", 1980, 165, 380, 85,
       ACC)
b.node("p2", "policy.sweep.sweep()\nover every open appeal", 1980, 285, 380, 70)
b.node("p3", "deadline_at_risk\nyour window is closing", 1980, 385, 380, 70)
b.node("p4", "insurer_overdue\nthe plan is late answering you", 1980, 475, 380, 70)
b.node("p5", "unreadable\nrefuses that one appeal in words you can\nact on, and carries "
             "on with the rest of the file", 1980, 565, 380, 95)
b.edge("pa", "p1", "p2", "", EDGE_ACC, exit=(0.5, 1), entry=(0.5, 0))
b.edge("pb", "p2", "p3", "", EDGE, exit=(0.5, 1), entry=(0.5, 0))
b.edge("pc", "p3", "p4", "", EDGE, exit=(0.5, 1), entry=(0.5, 0))
b.edge("pd", "p4", "p5", "", EDGE, exit=(0.5, 1), entry=(0.5, 0))

b.node("n1", "These three fire at every autonomy level, the most permissive included. "
             "Every other rule waits to be provoked by a tool call; this one fires "
             "because the agent is about to do nothing. A background agent that only "
             "spoke when provoked would go quiet through six months of a 180-day "
             "window and be right about everything except the thing that mattered.",
       1980, 700, 380, 130, NOTE)
b.node("n2", "Nothing is committed before the pause. A held decision leaves the journal "
             "empty for that step — it stopped before it did anything, not after.",
       1980, 850, 380, 80, NOTE)
b.node("n3", "Strands Agents on Amazon Bedrock. The model reasons; it never does the "
             "arithmetic. Every clock is a pure function over a notice date, a plan's "
             "rules and a stage.", 1980, 950, 380, 90, NOTE)

XML = ('<mxfile host="app.diagrams.net" type="device">\n' + a.xml("how-it-works")
       + b.xml("under-the-hood") + '</mxfile>\n')
OUT.write_text(XML, encoding="utf-8")
print(f"wrote {OUT}  ({len(a.cells)} cells)")
