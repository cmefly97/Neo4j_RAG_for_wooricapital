import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import { Fact } from "../api/client";

// etype 별 색 (덱/카드 색 체계와 통일)
const ETYPE_COLOR: Record<string, string> = {
  Product: "#18a66e",
  RateGrade: "#0e5a8a",
  Nego: "#c98a16",
  Decision: "#c0392b",
  VehicleCondition: "#7a5cc0",
  HandlingRule: "#2a8fb0",
  Term: "#5b6b7c",
  _n: "#aab4bf", // 관련(이웃) 노드
};

export default function FactsGraph({ facts }: { facts: Fact[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const nodes = new Map<string, any>();
    const edges: any[] = [];
    facts.forEach((f) => {
      if (!f.label) return;
      if (!nodes.has(f.label))
        nodes.set(f.label, { data: { id: f.label, label: f.label, color: ETYPE_COLOR[f.etype] || "#4f8cff", etype: f.etype } });
      (f.rels || []).forEach((r) => {
        if (!r || !r.target) return;
        if (!nodes.has(r.target))
          nodes.set(r.target, { data: { id: r.target, label: r.target, color: ETYPE_COLOR._n, etype: "관련" } });
        edges.push({ data: { source: f.label, target: r.target, label: r.rel || "" } });
      });
    });

    const cy = cytoscape({
      container: ref.current,
      elements: [...nodes.values(), ...edges],
      style: ([
        {
          selector: "node",
          style: {
            label: "data(label)", "font-size": 13, "background-color": "data(color)",
            color: "#1b2733", "text-valign": "bottom", "text-margin-y": 7,
            width: 42, height: 42, "border-width": 2, "border-color": "#fff",
            "text-background-color": "#fff", "text-background-opacity": 0.9,
            "text-background-padding": 3, "text-wrap": "wrap", "text-max-width": "130px",
          },
        },
        {
          selector: "edge",
          style: {
            label: "data(label)", "font-size": 10, color: "#5b6b7c", width: 1.8,
            "line-color": "#c4ccd4", "target-arrow-color": "#c4ccd4",
            "target-arrow-shape": "triangle", "curve-style": "bezier",
            "text-background-color": "#fff", "text-background-opacity": 0.9, "text-background-padding": 2,
          },
        },
      ]) as any,
      layout: { name: "cose", animate: false, padding: 30,
                nodeRepulsion: 9000, componentSpacing: 80, idealEdgeLength: 70 } as any,
    });
    // 노드가 적을 때 너무 작/크게 보이지 않도록 zoom 범위 제한 후 맞춤
    cy.minZoom(0.3); cy.maxZoom(1.8);
    cy.fit(undefined, 50);
    if (cy.zoom() > 1.6) cy.zoom(1.6), cy.center();
    return () => cy.destroy();
  }, [facts]);

  return <div ref={ref} style={{ height: "58vh", width: "100%", background: "#fbfcfd", borderRadius: 8 }} />;
}
