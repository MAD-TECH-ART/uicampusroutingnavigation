"""
visualize.py
------------
Renders the campus graph and computed routes to PNG images for use in the
project report and presentation slides.
"""

import matplotlib.pyplot as plt
from campus_graph import CampusGraph
from dijkstra import dijkstra
from shuttle_planner import plan_shuttle_route

CATEGORY_COLORS = {
    "hall": "#2E6F9E",
    "faculty": "#C7511F",
    "institute": "#8B5CF6",
    "landmark": "#4C9F70",
    "gate": "#7C5CBF",
}
CATEGORY_LABELS = {
    "hall": "Hall of Residence",
    "faculty": "Faculty / Academic",
    "institute": "Institute",
    "landmark": "Key Landmark",
    "gate": "Gate",
}


def draw_base_map(graph: CampusGraph, ax, fontsize=6.5):
    # Draw all edges (roads)
    drawn = set()
    for a in graph.adjacency:
        for b, _w in graph.adjacency[a]:
            key = tuple(sorted((a, b)))
            if key in drawn:
                continue
            drawn.add(key)
            na, nb = graph.nodes[a], graph.nodes[b]
            ax.plot([na.x, nb.x], [na.y, nb.y], color="#CCCCCC", linewidth=1.3, zorder=1)

    # Draw nodes
    for nid, node in graph.nodes.items():
        color = CATEGORY_COLORS.get(node.category, "gray")
        ax.scatter(node.x, node.y, s=110, color=color, edgecolor="white",
                   linewidth=1.0, zorder=3)
        ax.annotate(node.name, (node.x, node.y), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=fontsize, zorder=4)


def plot_campus_network(graph: CampusGraph, save_path: str):
    fig, ax = plt.subplots(figsize=(15, 11))
    draw_base_map(graph, ax)

    handles = [plt.Line2D([0], [0], marker='o', color='w', label=lbl,
                           markerfacecolor=col, markersize=10)
               for col, lbl in zip(CATEGORY_COLORS.values(), CATEGORY_LABELS.values())]
    ax.legend(handles=handles, loc="lower right", fontsize=10, frameon=True)

    ax.set_title(f"University of Ibadan Campus Road Network (Model) — {len(graph.nodes)} locations",
                 fontsize=15, fontweight="bold")
    ax.set_xlabel("metres (relative)")
    ax.set_ylabel("metres (relative)")
    ax.set_aspect("equal")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def plot_shortest_path(graph: CampusGraph, source: str, target: str, save_path: str,
                        congestion_model=None, time_profile: str = "off_peak"):
    path, dist = dijkstra(graph, source, target, congestion_model=congestion_model, time_profile=time_profile)

    fig, ax = plt.subplots(figsize=(15, 11))
    draw_base_map(graph, ax)

    xs = [graph.nodes[n].x for n in path]
    ys = [graph.nodes[n].y for n in path]
    ax.plot(xs, ys, color="#D62839", linewidth=3.5, zorder=2,
             solid_capstyle="round", label="Shortest path")
    for n in path:
        node = graph.nodes[n]
        ax.scatter(node.x, node.y, s=220, facecolor="none", edgecolor="#D62839",
                   linewidth=2.5, zorder=5)

    ax.set_title(
        f"Shortest Route: {graph.nodes[source].name} -> {graph.nodes[target].name}\n"
        f"Distance: {dist:.0f} m",
        fontsize=13, fontweight="bold")
    ax.set_aspect("equal")
    ax.set_xlabel("metres (relative)")
    ax.set_ylabel("metres (relative)")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    return path, dist


def plot_shuttle_route(graph: CampusGraph, depot: str, stops, save_path: str,
                        congestion_model=None, time_profile: str = "off_peak"):
    result = plan_shuttle_route(graph, depot, stops, congestion_model=congestion_model, time_profile=time_profile)
    route = result["optimized_route"]

    fig, ax = plt.subplots(figsize=(15, 11))
    draw_base_map(graph, ax)

    # Draw the actual shortest sub-paths between consecutive stops
    from dijkstra import dijkstra as dj
    for i in range(len(route) - 1):
        sub_path, _ = dj(graph, route[i], route[i + 1], congestion_model=congestion_model, time_profile=time_profile)
        xs = [graph.nodes[n].x for n in sub_path]
        ys = [graph.nodes[n].y for n in sub_path]
        ax.plot(xs, ys, color="#1D8A99", linewidth=3, zorder=2, alpha=0.85)

    for order, n in enumerate(route):
        node = graph.nodes[n]
        ax.scatter(node.x, node.y, s=250, facecolor="#FFC857", edgecolor="#1D8A99",
                   linewidth=2, zorder=5)
        ax.annotate(str(order), (node.x, node.y), fontsize=8, fontweight="bold",
                    ha="center", va="center", zorder=6)

    ax.set_title(
        f"Optimized Shuttle Route (Depot: {graph.nodes[depot].name})\n"
        f"Total distance: {result['optimized_distance']:.0f} m | Stops: {len(stops)}",
        fontsize=13, fontweight="bold")
    ax.set_aspect("equal")
    ax.set_xlabel("metres (relative)")
    ax.set_ylabel("metres (relative)")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    return result


if __name__ == "__main__":
    g = CampusGraph()
    plot_campus_network(g, "../assets/campus_network.png")
    plot_shortest_path(g, "MAIN_GATE", "FAC_DENTISTRY", "../assets/shortest_path_demo.png")
    plot_shuttle_route(g, "MAIN_GATE",
                        ["MELLANBY", "KUTI", "SULTAN_BELLO", "QUEEN_IDIA", "AWOLOWO_PG", "FAC_TECH", "ALEX_BROWN"],
                        "../assets/shuttle_route_demo.png")
    print("Saved: campus_network.png, shortest_path_demo.png, shuttle_route_demo.png")
