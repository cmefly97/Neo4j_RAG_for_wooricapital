import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";

type Props = { nodes: any[]; edges: any[] };

export default function GraphView({ nodes, edges }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const cy = cytoscape({
      container: ref.current,
      elements: [
        ...nodes.map((n) => ({ data: { id: n.id, label: n.label } })),
        ...edges
          .filter((e) => nodes.find((n) => n.id === e.source) && nodes.find((n) => n.id === e.target))
          .map((e) => ({ data: { source: e.source, target: e.target, label: e.relation } })),
      ],
      style: [
        { selector: "node", style: { label: "data(label)", "font-size": 8, "background-color": "#4f8cff" } },
        { selector: "edge", style: { label: "data(label)", "font-size": 6, "line-color": "#bbb", "target-arrow-shape": "triangle", "curve-style": "bezier" } },
      ],
      layout: { name: "cose" },
    });
    return () => cy.destroy();
  }, [nodes, edges]);

  return <div ref={ref} style={{ height: 500, border: "1px solid #ddd" }} />;
}
