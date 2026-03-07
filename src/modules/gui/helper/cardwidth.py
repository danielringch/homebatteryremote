from nicegui import ui

SYNC_WIDTH_CARD_CLASS = "sync-width-card"

def sync_card_widths(card_class: str = SYNC_WIDTH_CARD_CLASS):
    ui.run_javascript(f'''
    function syncWidths() {{
        const cards = Array.from(document.getElementsByClassName("{card_class}"));
        if (!cards.length) return;

        let maxWidth = 0;

        cards.forEach(c => c.style.width = "auto");

        cards.forEach(c => {{
            maxWidth = Math.max(maxWidth, c.offsetWidth);
        }});

        cards.forEach(c => {{
            c.style.width = maxWidth + "px";
        }});
    }}

    // run initially
    setTimeout(syncWidths, 50);

    // update when window resizes
    window.addEventListener("resize", syncWidths);
    ''')