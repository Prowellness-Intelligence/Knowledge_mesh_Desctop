"""
Script to generate a simple mockup of the Knowledge Mesh Desktop UI.

This script creates a visualization of the UI with dark theme, glowing elements,
and knowledge mesh visualization without relying on external AI services or complex effects.
"""

import sys
import os
import asyncio
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))


async def generate_ui_mockup():
    """Generate a simple mockup of the Knowledge Mesh Desktop UI."""
    print("Generating UI mockup...")
    
    output_dir = Path("./mockups")
    output_dir.mkdir(exist_ok=True)
    
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(16, 9), dpi=100)
    fig.patch.set_facecolor('#121212')
    ax.set_facecolor('#121212')
    
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    main_window = patches.Rectangle((0.05, 0.05), 0.9, 0.9, linewidth=1, 
                                   edgecolor='#30D5C8', facecolor='#121212',
                                   alpha=0.7, zorder=1)
    ax.add_patch(main_window)
    
    sidebar = patches.Rectangle((0.05, 0.05), 0.06, 0.9, linewidth=1,
                              edgecolor='#30D5C8', facecolor='#1A1A1A',
                              alpha=0.9, zorder=3)
    ax.add_patch(sidebar)
    
    icon_positions = [0.08, 0.15, 0.22, 0.29, 0.36, 0.43, 0.50]
    for pos in icon_positions:
        icon = patches.Circle((0.08, pos), 0.02, linewidth=1,
                            edgecolor='#30D5C8', facecolor='#30D5C8',
                            alpha=0.8, zorder=4)
        ax.add_patch(icon)
    
    search_bar = patches.Rectangle((0.15, 0.88), 0.8, 0.05, linewidth=1,
                                 edgecolor='#30D5C8', facecolor='#1A1A1A',
                                 alpha=0.8, zorder=3)
    ax.add_patch(search_bar)
    ax.text(0.18, 0.905, "Search emails, documents, and knowledge...", color='#888888', fontsize=10, zorder=4)
    
    email_panel = patches.Rectangle((0.15, 0.15), 0.25, 0.7, linewidth=1,
                                  edgecolor='#30D5C8', facecolor='#1A1A1A',
                                  alpha=0.7, zorder=3)
    ax.add_patch(email_panel)
    ax.text(0.16, 0.82, "Emails", color='#FFFFFF', fontsize=12, fontweight='bold', zorder=4)
    
    email_positions = [0.78, 0.71, 0.64, 0.57, 0.50, 0.43, 0.36, 0.29, 0.22]
    for i, pos in enumerate(email_positions):
        email_item = patches.Rectangle((0.16, pos - 0.05), 0.23, 0.06, linewidth=1,
                                     edgecolor='#30D5C8', facecolor='#252525',
                                     alpha=0.8, zorder=4)
        ax.add_patch(email_item)
        ax.text(0.17, pos - 0.01, f"Email {i+1}: Important update", color='#FFFFFF', fontsize=8, zorder=5)
        ax.text(0.17, pos - 0.04, "From: user@example.com", color='#AAAAAA', fontsize=6, zorder=5)
    
    doc_panel = patches.Rectangle((0.7, 0.15), 0.25, 0.7, linewidth=1,
                                edgecolor='#30D5C8', facecolor='#1A1A1A',
                                alpha=0.7, zorder=3)
    ax.add_patch(doc_panel)
    ax.text(0.71, 0.82, "Document Viewer", color='#FFFFFF', fontsize=12, fontweight='bold', zorder=4)
    
    for i in range(15):
        y_pos = 0.78 - i * 0.04
        width = np.random.uniform(0.15, 0.23)
        ax.plot([0.71, 0.71 + width], [y_pos, y_pos], color='#BBBBBB', linewidth=1, alpha=0.7, zorder=4)
    
    mesh_panel = patches.Rectangle((0.43, 0.25), 0.24, 0.5, linewidth=1,
                                 edgecolor='#30D5C8', facecolor='#1A1A1A',
                                 alpha=0.7, zorder=3)
    ax.add_patch(mesh_panel)
    ax.text(0.44, 0.72, "Knowledge Mesh", color='#FFFFFF', fontsize=12, fontweight='bold', zorder=4)
    
    nodes = []
    node_positions = [
        (0.55, 0.65), (0.48, 0.55), (0.58, 0.45), 
        (0.5, 0.35), (0.53, 0.5), (0.46, 0.45),
        (0.52, 0.4), (0.6, 0.55), (0.45, 0.6)
    ]
    
    for i, (x, y) in enumerate(node_positions):
        node = patches.Circle((x, y), 0.015, linewidth=1,
                            edgecolor='#30D5C8', facecolor='#30D5C8',
                            alpha=0.8, zorder=5)
        ax.add_patch(node)
        nodes.append((x, y))
    
    connections = [
        (0, 1), (0, 2), (1, 3), (2, 3), (1, 4), 
        (2, 4), (3, 6), (4, 5), (5, 6), (0, 7),
        (7, 2), (1, 8), (8, 5)
    ]
    
    for i, j in connections:
        x1, y1 = nodes[i]
        x2, y2 = nodes[j]
        line = plt.Line2D([x1, x2], [y1, y2], color='#30D5C8', 
                         alpha=0.4, linewidth=1, zorder=4)
        ax.add_line(line)
    
    card_positions = [0.15, 0.43, 0.7]
    card_titles = ["Daily Summary", "Related Documents", "Upcoming Tasks"]
    
    for i, (pos, title) in enumerate(zip(card_positions, card_titles)):
        card = patches.Rectangle((pos, 0.07), 0.25, 0.06, linewidth=1,
                               edgecolor='#30D5C8', facecolor='#252525',
                               alpha=0.8, zorder=4)
        ax.add_patch(card)
        ax.text(pos + 0.01, 0.11, title, color='#FFFFFF', fontsize=10, fontweight='bold', zorder=5)
        ax.text(pos + 0.01, 0.08, "3 new items to review", color='#AAAAAA', fontsize=8, zorder=5)
    
    mockup_path = output_dir / "ui_mockup_dark.png"
    plt.savefig(mockup_path, dpi=300, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    
    print(f"Dark theme mockup generated and saved to: {mockup_path}")
    
    themes = {
        "blue": {"primary": "#0066CC", "secondary": "#0099FF", "bg": "#121212", "text": "#FFFFFF"},
        "green": {"primary": "#00CC66", "secondary": "#00FF99", "bg": "#121212", "text": "#FFFFFF"},
        "light": {"primary": "#888888", "secondary": "#CCCCCC", "bg": "#F5F5F5", "text": "#333333"}
    }
    
    for theme_name, colors in themes.items():
        fig, ax = plt.subplots(figsize=(16, 9), dpi=100)
        
        bg_color = colors["bg"]
        text_color = colors["text"]
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        main_window = patches.Rectangle((0.05, 0.05), 0.9, 0.9, linewidth=1, 
                                       edgecolor=colors["primary"], facecolor=bg_color,
                                       alpha=0.7, zorder=1)
        ax.add_patch(main_window)
        
        sidebar_bg = "#1A1A1A" if bg_color == "#121212" else "#E5E5E5"
        sidebar = patches.Rectangle((0.05, 0.05), 0.06, 0.9, linewidth=1,
                                  edgecolor=colors["primary"], facecolor=sidebar_bg,
                                  alpha=0.9, zorder=3)
        ax.add_patch(sidebar)
        
        icon_positions = [0.08, 0.15, 0.22, 0.29, 0.36, 0.43, 0.50]
        for pos in icon_positions:
            icon = patches.Circle((0.08, pos), 0.02, linewidth=1,
                                edgecolor=colors["primary"], facecolor=colors["primary"],
                                alpha=0.8, zorder=4)
            ax.add_patch(icon)
        
        ax.text(0.5, 0.95, f"Knowledge Mesh Desktop - {theme_name.capitalize()} Theme", 
               color=text_color, fontsize=16, fontweight='bold', ha='center', zorder=5)
        
        themed_mockup_path = output_dir / f"ui_mockup_{theme_name}.png"
        plt.savefig(themed_mockup_path, dpi=300, bbox_inches='tight', pad_inches=0.1)
        plt.close()
        
        print(f"{theme_name.capitalize()} theme mockup saved to: {themed_mockup_path}")
    
    return str(mockup_path)


if __name__ == "__main__":
    asyncio.run(generate_ui_mockup())
