from docchat.cleaning import clean_pages, find_boilerplate


def _body(i, lines=8):
    """A realistic page body: enough lines that header/footer lines are only at the edges."""
    return "\n".join(
        f"The committee reviewed item {i}-{n} and then recorded decision number {i * n} in the quarterly plan."
        for n in range(lines)
    )


def _pages(n):
    return [f"My Report 2024\n{_body(i)}\nPage {i}\n" for i in range(1, n + 1)]


def test_repeated_header_and_page_numbers_are_removed():
    cleaned = clean_pages(_pages(5))
    assert "My Report" not in cleaned[2] and "Page 3" not in cleaned[2]
    assert cleaned[2].startswith("The committee reviewed item 3-0")
    assert cleaned[2].endswith("decision number 21 in the quarterly plan.")


def test_header_with_changing_digits_still_counts_as_repeated():
    pages = [f"Chapter {i} - Handbook\n{_body(i)}\n{i}\n" for i in range(1, 6)]
    assert "chapter # - handbook" in find_boilerplate(pages)
    assert not clean_pages(pages)[0].lower().startswith("chapter")


def test_short_documents_keep_their_first_lines():
    # with only two pages "repeats on most pages" means nothing, so nothing is dropped
    pages = ["Title\nfirst page text", "Title\nsecond page text"]
    assert clean_pages(pages)[0].startswith("Title")


def test_hyphenated_line_breaks_are_joined():
    cleaned = clean_pages(["Delivery restric-\ntions apply to all orders."])
    assert cleaned == ["Delivery restrictions apply to all orders."]


def test_real_hyphens_before_capitals_or_digits_are_kept():
    # only a lowercase letter after the break means "split word"; digits and capitals are left alone
    cleaned = clean_pages(["Call 1-\n800 or read the X-\nRay notes."])
    assert cleaned == ["Call 1- 800 or read the X- Ray notes."]


def test_wrapped_lines_become_one_paragraph_and_blank_lines_split_paragraphs():
    cleaned = clean_pages(["one two\nthree four\n\nfive   six"])
    assert cleaned == ["one two three four\n\nfive six"]


def test_ligatures_and_control_characters_are_normalised():
    cleaned = clean_pages(["The ﬁnal oﬃce\x00 plan"])
    assert cleaned == ["The final office plan"]


def test_output_keeps_one_entry_per_page_even_if_a_page_is_empty():
    pages = ["Header\n1\n", "Header\nText\n2\n", "Header\n3\n"]
    cleaned = clean_pages(pages)
    assert len(cleaned) == 3 and cleaned[0] == "" and cleaned[2] == ""


def test_templated_body_lines_are_not_mistaken_for_headers():
    # every page opens and closes with a long line that differs only by digits
    pages = [f"Step {i}: remove the cover plate and check that all six fixing screws are present\n{_body(i)}\n"
             f"Step {i}0: refit the cover plate and tighten the fixing screws evenly by hand\n" for i in range(1, 6)]
    assert find_boilerplate(pages) == set()
    assert clean_pages(pages)[1].startswith("Step 2: remove the cover plate")
