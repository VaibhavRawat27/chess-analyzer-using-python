import streamlit as st
import chess
import chess.svg
from stockfish import Stockfish
import base64
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

# Stockfish path
STOCKFISH_PATH = "stockfish.exe"  # Update if needed

# Initialize Stockfish
stockfish = Stockfish(path=STOCKFISH_PATH)
stockfish.set_skill_level(15)

# Setup board and evals
if "board" not in st.session_state:
    st.session_state.board = chess.Board()
if "evals" not in st.session_state:
    st.session_state.evals = []
if "move_history" not in st.session_state:
    st.session_state.move_history = []

# Render SVG
def render_svg(svg, size=600):
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f'<img src="data:image/svg+xml;base64,{b64}" width="{size}"/>'

# Smaller evaluation bar
def draw_eval_bar(score_cp):
    score = max(min(score_cp, 1000), -1000)
    fig, ax = plt.subplots(figsize=(0.1, 0.5))  # Smaller dimensions (width, height)
    ax.axis('off')

    # Background bar (white on top, black on bottom)
    ax.add_patch(patches.Rectangle((0, 0), 1, 1000, color="black"))
    ax.add_patch(patches.Rectangle((0, 1000), 1, 1000, color="white"))

    # Normalize score to range 0-2000
    bar_height = 1000 + score
    ax.add_patch(patches.Rectangle((0, 0), 1, bar_height, color="#4CAF50"))

    ax.set_ylim(0, 2000)
    ax.set_xlim(0, 1)
    plt.tight_layout()
    return fig

# Page config
st.set_page_config(layout="wide")
st.title("♟️ Advanced Chess Analyzer")

# Input
user_move = st.text_input("Enter your move (UCI format, e.g., e2e4):", key="uci_input")

# Layout
col_eval, col_board, col_data = st.columns([1, 2, 3])

# Eval bar
with col_eval:
    st.markdown("### 🔍 Eval Bar")
    if not st.session_state.board.is_game_over():
        stockfish.set_fen_position(st.session_state.board.fen())
        eval_data = stockfish.get_evaluation()
        eval_score = eval_data["value"] if eval_data["type"] == "cp" else (1000 if eval_data["value"] > 0 else -1000)
        st.session_state.evals.append(eval_score)
        st.pyplot(draw_eval_bar(eval_score))
    else:
        st.info("Game over.")


# Board
with col_board:
    st.markdown("### ♟️ Chess Board")
    last_move = st.session_state.board.peek() if st.session_state.board.move_stack else None
    svg = chess.svg.board(st.session_state.board, lastmove=last_move, size=600)
    st.markdown(render_svg(svg), unsafe_allow_html=True)

# Move action & data
with col_data:
    st.markdown("### 🧠 Move Actions")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("▶️ Play Move"):
            try:
                move = chess.Move.from_uci(user_move.strip())
                if move in st.session_state.board.legal_moves:
                    st.session_state.board.push(move)

                    stockfish.set_fen_position(st.session_state.board.fen())
                    played_eval = stockfish.get_evaluation()
                    best_move = stockfish.get_best_move()

                    stockfish.set_fen_position(st.session_state.board.fen())
                    stockfish.make_moves_from_current_position([best_move])
                    best_eval = stockfish.get_evaluation()

                    def move_quality(score1, score2):
                        if score1["type"] != score2["type"]:
                            return "Unclear ❓"
                        diff = abs(score1["value"] - score2["value"])
                        if diff < 30:
                            return "Excellent ✅"
                        elif diff < 80:
                            return "Good 👍"
                        elif diff < 150:
                            return "Inaccuracy ⚠️"
                        elif diff < 300:
                            return "Mistake ❌"
                        else:
                            return "Blunder 💥"

                    quality = move_quality(played_eval, best_eval)

                    st.session_state["last_data"] = {
                        "user_move": user_move,
                        "best_move": best_move,
                        "quality": quality,
                        "eval": played_eval
                    }

                    # Update move history
                    st.session_state.move_history.append({
                        "Your Move": user_move,
                        "Best Move": best_move,
                        "Move Quality": quality,
                        "Eval": played_eval["value"]
                    })

                    # Re-render the board after the move
                    last_move = st.session_state.board.peek() if st.session_state.board.move_stack else None
                    svg = chess.svg.board(st.session_state.board, lastmove=last_move, size=600)
                    st.markdown(render_svg(svg), unsafe_allow_html=True)

                else:
                    st.error("Illegal move.")
            except Exception as e:
                st.error(f"Invalid move format: {e}")

    with col2:
        if st.button("↩️ Undo"):
            if st.session_state.board.move_stack:
                st.session_state.board.pop()
                if st.session_state.evals:
                    st.session_state.evals.pop()
                if st.session_state.move_history:
                    st.session_state.move_history.pop()

    with col3:
        if st.button("🔄 Reset"):
            st.session_state.board.reset()
            st.session_state.evals = []
            st.session_state.move_history = []
            st.session_state["last_data"] = {}

    # Show move summary cards
    st.markdown("### 🗂️ Move Summary")
    data = st.session_state.get("last_data", {})
    if data:
        cards = st.columns(4)
        cards[0].metric("Your Move", data.get("user_move", "-"))
        cards[1].metric("Best Move", data.get("best_move", "-"))
        cards[2].metric("Move Quality", data.get("quality", "-"))
        cards[3].metric("Eval", str(data.get("eval", {}).get("value", "-")))
    else:
        st.write("No data yet.")

# Move history
st.markdown("### 📜 Move History")
if st.session_state.move_history:
    move_df = pd.DataFrame(st.session_state.move_history)
    st.table(move_df)
else:
    st.write("No moves yet.")

# Evaluation chart
with st.expander("📈 Show Evaluation Chart"):
    if st.session_state.evals:
        fig, ax = plt.subplots()
        ax.plot(st.session_state.evals, marker="o")
        ax.set_title("Evaluation Over Time (centipawns)")
        ax.set_xlabel("Move Number")
        ax.set_ylabel("Evaluation")
        st.pyplot(fig)
    else:
        st.info("No data yet.")
