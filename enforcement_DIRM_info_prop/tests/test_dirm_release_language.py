import re
import unittest

from dirm import build_example_6_bts, build_simplified_example_2_bts, JState, LState
from dirm.release_language import (
    EPSILON, Language, recursive_transition_labels,
)


def _python_regex(language: Language) -> str:
    """Independent matcher for checking bounded words in a path language."""
    if language.kind == "empty":
        return r"(?!)"
    if language.kind == "epsilon":
        return ""
    if language.kind == "symbol":
        return re.escape(language.symbol)
    if language.kind == "union":
        return "(?:" + "|".join(map(_python_regex, language.parts)) + ")"
    if language.kind == "concat":
        return "".join(map(_python_regex, language.parts))
    if language.kind in {"star", "plus"}:
        suffix = "*" if language.kind == "star" else "+"
        return "(?:" + _python_regex(language.parts[0]) + ")" + suffix
    raise AssertionError(language.kind)


class ReleaseLanguageTests(unittest.TestCase):
    def test_example_6_same_low_and_gamma_have_different_release_successors(self):
        bts = build_example_6_bts()
        gamma = bts.plant.alphabet
        low = frozenset({(2, True), (3, True)})
        branches = [JState(frozenset({(q, True)}), low, gamma) for q in (2, 3)]
        self.assertEqual(bts.control_patterns(), (gamma,))
        self.assertEqual(bts.system.release_states, {4, 5})
        for branch, first_target in zip(branches, (4, 5)):
            self.assertIn(branch, bts.graph)
            releases = [edge for edge in bts.graph[branch] if edge.kind == "JL"]
            self.assertTrue(all(isinstance(edge.target, LState) for edge in releases))
            for count in range(7):
                word = "h" * count + "o3"
                matched = {
                    edge.target.q_mid for edge in releases
                    if re.fullmatch(_python_regex(edge.release_language), word)
                }
                expected = first_target if count % 2 == 0 else 9 - first_target
                self.assertEqual(matched, {frozenset({(expected, True)})}, word)
        # With no controllable event, the secret release cannot be prevented.
        self.assertFalse(bts.synthesize().initial_winning)

    def test_example_2_distinguishes_one_h_from_looped_h(self):
        bts = build_simplified_example_2_bts()
        root = next(
            edge.target for edge in bts.graph[bts.initial]
            if edge.gamma == bts.plant.alphabet
        )
        releases = {
            (edge.sigma, edge.target.q_mid): edge.release_language
            for edge in bts.graph[root] if edge.kind == "JL"
        }
        pair = frozenset({("2", True), ("5", True)})
        two = frozenset({("2", True)})
        five = frozenset({("5", True)})
        self.assertEqual(str(releases["a", pair]), "h")
        self.assertEqual(str(releases["b", pair]), "h")
        self.assertEqual(str(releases["b", five]), "hh^+")
        for word in ("", "h", "hh", "hhh", "ho", "hho", "hhho"):
            self.assertEqual(
                re.fullmatch(_python_regex(releases["b", five]), word) is not None,
                word in {"hh", "hhh"},
            )
            self.assertEqual(
                re.fullmatch(_python_regex(releases["o", two]), word) is not None,
                word in {"ho", "hho", "hhho"},
            )
        self.assertEqual(dict(bts.state_counts()), {"I": 7, "J": 29, "L": 5})

    def test_overlapping_and_sequential_cycles_match_finite_walks(self):
        graph = {
            "s": (("a", "u"),),
            "u": (("b", "v"),),
            "v": (("c", "u"), ("g", "z"), ("d", "w")),
            "z": (("k", "v"),),
            "w": (("e", "w"), ("f", "t")),
            "t": (),
        }
        # Check generated walks and a focused set of excluded alternatives;
        # full alphabet enumeration would obscure this test's purpose.
        candidates = {
            "a", "ab", "abc", "abd", "abdf", "abdef", "abcbdf",
            "ac", "acdf", "abcdef", "abde", "abcbde", "abcbdfg",
            "abgkdf", "abgdf", "abgk", "abgkdef",
        }
        for start in graph:
            walks = {start: {""}}
            for _ in range(7):
                later = {node: set(words) for node, words in walks.items()}
                for node, words in walks.items():
                    for event, target in graph[node]:
                        later.setdefault(target, set()).update(
                            word + event for word in words
                        )
                walks = later
            candidates.update(walks.get("t", set()))
            release = recursive_transition_labels(
                graph, start, {"t": {"release": EPSILON}}
            )["release"]
            matcher = _python_regex(release)
            for word in candidates:
                self.assertEqual(
                    re.fullmatch(matcher, word) is not None,
                    word in walks.get("t", set()),
                    (start, word, str(release)),
                )


if __name__ == "__main__":
    unittest.main()
