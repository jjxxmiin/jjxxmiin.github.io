"""A six-second, silent ManimGL loop that makes 268 / 285 legible."""

from manimlib import *


OFF_WHITE = "#F4F1E8"
INK = "#0B0D0E"
COBALT = "#245BFF"
MINT = "#56E5C3"
MUTED = "#7D817F"
FONT = "Noto Sans CJK KR"


def copy(text, size, color=INK, weight="NORMAL"):
  """Create consistently styled text without requiring LaTeX."""
  return Text(
    text,
    font=FONT,
    font_size=size,
    fill_color=color,
    base_color=color,
    weight=weight,
  )


class Ratio268Of285(Scene):
  default_camera_config = {
    "background_color": OFF_WHITE,
  }

  def construct(self):
    top_rule = Line(LEFT * 6.45, RIGHT * 6.45)
    top_rule.set_stroke(INK, width=2, opacity=0.18)
    top_rule.set_y(3.35)

    eyebrow = copy("MATH · MADE VISIBLE", 24, COBALT, "BOLD")
    eyebrow.to_edge(LEFT, buff=0.68).set_y(3.02)

    issue = copy("285명 중 268명", 56, INK, "BOLD")
    issue.to_edge(LEFT, buff=0.66).set_y(2.34)

    kicker = copy("얼마나 큰 비율일까?", 30, MUTED)
    kicker.to_edge(LEFT, buff=0.69).set_y(1.77)

    number = copy("94", 246, INK, "BOLD")
    percent = copy("%", 104, COBALT, "BOLD")
    percent.next_to(number, RIGHT, buff=0.08)
    percent.align_to(number, UP).shift(DOWN * 0.21)
    answer = VGroup(number, percent)
    answer.move_to(LEFT * 3.63 + UP * 0.15)

    approx = copy("≈", 42, COBALT, "BOLD")
    equation = copy("268 ÷ 285 = 0.94035…", 35, INK, "BOLD")
    equation_row = VGroup(approx, equation).arrange(RIGHT, buff=0.18)
    equation_row.move_to(LEFT * 3.66 + DOWN * 1.38)

    note_bar = RoundedRectangle(
      width=4.48,
      height=0.72,
      corner_radius=0.14,
      fill_color=MINT,
      fill_opacity=1,
      stroke_width=0,
    )
    note_bar.move_to(LEFT * 3.65 + DOWN * 2.22)
    note = copy("소수점 첫째 자리에서 반올림", 26, INK, "BOLD")
    note.move_to(note_bar)

    footer = copy("268 ÷ 285 × 100", 23, MUTED)
    footer.to_edge(LEFT, buff=0.69).set_y(-3.12)

    card = RoundedRectangle(
      width=5.35,
      height=6.34,
      corner_radius=0.28,
      fill_color=INK,
      fill_opacity=1,
      stroke_width=0,
    )
    card.move_to(RIGHT * 3.75 + DOWN * 0.05)

    card_title = copy("285칸", 31, OFF_WHITE, "BOLD")
    card_title.move_to(card.get_top() + DOWN * 0.48 + LEFT * 1.72)
    one_cell = copy("1칸 = 1명", 21, MINT, "BOLD")
    one_cell.move_to(card.get_top() + DOWN * 0.49 + RIGHT * 1.63)

    cells = VGroup()
    empty_cells = VGroup()
    for index in range(285):
      cell = Square(side_length=0.178)
      if index < 268:
        cell.set_fill(COBALT, opacity=1)
        cell.set_stroke(COBALT, width=0)
      else:
        cell.set_fill(MINT, opacity=0.18)
        cell.set_stroke(MINT, width=1.2, opacity=0.58)
        empty_cells.add(cell)
      cells.add(cell)
    cells.arrange_in_grid(n_rows=19, n_cols=15, buff=0.050)
    cells.move_to(card.get_center() + UP * 0.07)

    legend_filled_mark = Square(
      side_length=0.16,
      fill_color=COBALT,
      fill_opacity=1,
      stroke_width=0,
    )
    legend_filled = copy("268 채움", 22, OFF_WHITE, "BOLD")
    legend_filled_group = VGroup(legend_filled_mark, legend_filled)
    legend_filled_group.arrange(RIGHT, buff=0.13)

    legend_empty_mark = Square(
      side_length=0.16,
      fill_color=MINT,
      fill_opacity=0.30,
      stroke_color=MINT,
      stroke_width=1.2,
    )
    legend_empty = copy("17 남음", 22, OFF_WHITE, "BOLD")
    legend_empty_group = VGroup(legend_empty_mark, legend_empty)
    legend_empty_group.arrange(RIGHT, buff=0.13)

    legend = VGroup(legend_filled_group, legend_empty_group)
    legend.arrange(RIGHT, buff=0.56)
    legend.move_to(card.get_bottom() + UP * 0.43)

    self.add(
      top_rule,
      eyebrow,
      issue,
      kicker,
      answer,
      equation_row,
      note_bar,
      note,
      footer,
      card,
      card_title,
      one_cell,
      cells,
      legend,
    )

    def animate_remainder(group, alpha):
      for index, cell in enumerate(group):
        wave = 0.5 + 0.5 * np.cos(TAU * (alpha - index / len(group)))
        cell.set_fill(MINT, opacity=0.12 + 0.56 * wave)
        cell.set_stroke(MINT, width=1.2, opacity=0.40 + 0.60 * wave)
      return group

    # The wave begins and ends in the same state for a clean video loop.
    animate_remainder(empty_cells, 0)
    self.wait(0.3)
    self.play(
      UpdateFromAlphaFunc(empty_cells, animate_remainder, rate_func=linear),
      run_time=5.4,
    )
    animate_remainder(empty_cells, 0)
    self.wait(0.3)
