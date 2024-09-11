# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2024)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""button_group unit test."""

from __future__ import annotations

from typing import Any, Callable
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from parameterized import parameterized

import streamlit as st
from streamlit.elements.widgets.button_group import (
    _FACES_ICONS,
    _SELECTED_STAR_ICON,
    _STAR_ICON,
    _THUMB_ICONS,
    ButtonGroupMixin,
    FeedbackSerde,
    get_mapped_options,
)
from streamlit.errors import StreamlitAPIException
from streamlit.proto.ButtonGroup_pb2 import ButtonGroup as ButtonGroupProto
from streamlit.proto.LabelVisibilityMessage_pb2 import LabelVisibilityMessage
from streamlit.runtime.state.session_state import get_script_run_ctx
from tests.delta_generator_test_case import DeltaGeneratorTestCase


class TestGetMappedOptions:
    def test_thumbs(self):
        options, options_indices = get_mapped_options("thumbs")

        assert len(options) == 2
        assert len(options_indices) == 2

        for index, option in enumerate(options):
            assert option.content_icon == _THUMB_ICONS[index]

        # ensure order of thumbs
        assert "down" in options[1].content_icon
        assert options_indices[0] == 1
        assert "up" in options[0].content_icon
        assert options_indices[1] == 0

    def test_faces(self):
        options, options_indices = get_mapped_options("faces")

        assert len(options) == 5
        assert len(options_indices) == 5

        for index, option in enumerate(options):
            assert option.content_icon == _FACES_ICONS[index]
            assert option.selected_content_icon == ""
            assert options_indices[index] == index

        # ensure order of faces
        assert "sad" in options[0].content_icon
        assert "very_satisfied" in options[4].content_icon

    def test_stars(self):
        options, options_indices = get_mapped_options("stars")

        assert len(options) == 5
        assert len(options_indices) == 5

        for index, option in enumerate(options):
            assert option.content_icon == _STAR_ICON
            assert option.selected_content_icon == _SELECTED_STAR_ICON
            assert options_indices[index] == index


class TestFeedbackSerde:
    def test_serialize(self):
        option_indices = [5, 6, 7]
        serde = FeedbackSerde(option_indices)
        res = serde.serialize(6)
        assert res == [1]

    def test_serialize_raise_option_does_not_exist(self):
        option_indices = [5, 6, 7]
        serde = FeedbackSerde(option_indices)

        with pytest.raises(StreamlitAPIException):
            serde.serialize(8)

    def test_deserialize(self):
        option_indices = [5, 6, 7]
        serde = FeedbackSerde(option_indices)
        res = serde.deserialize([1], "")
        assert res == 6

    def test_deserialize_raise_indexerror(self):
        option_indices = [5, 6, 7]
        serde = FeedbackSerde(option_indices)

        with pytest.raises(IndexError):
            serde.deserialize([3], "")


class TestFeedbackCommand(DeltaGeneratorTestCase):
    """Tests that are specific for the feedback command."""

    def test_invalid_option_literal(self):
        with pytest.raises(StreamlitAPIException) as e:
            st.feedback("foo")
        assert (
            "The options argument to st.feedback must be one of "
            "['thumbs', 'faces', 'stars']. The argument passed was 'foo'."
        ) == str(e.value)


def get_command_matrix(
    test_args: list[Any], with_st_feedback: bool = False
) -> list[tuple[Any]]:
    """Return a test matrix for the different button group commands and the
    passed arguments.

    If the test args is a list like [("foo", ("a", "b")), ("bar", ("c", "d"))],
    this function returns following test matrix:
    [(st.pills, "foo", ("a", "b")), (_interal_button_group, "bar", ("c", "d"))]

    The pills and _internal_button_group are wrapped in a lambda to pass default
    arguments that are not shared between them.
    """
    matrix = []

    commands = [
        lambda *args, **kwargs: st.pills("label", *args, **kwargs),
        lambda *args, **kwargs: ButtonGroupMixin._internal_button_group(
            st._main, *args, **kwargs
        ),
    ]
    if with_st_feedback:
        commands.append(lambda *args, **kwargs: st.feedback(*args, **kwargs))

    for command in commands:
        if command is None:
            continue
        if len(test_args) == 0:
            matrix.append((command,))
            continue

        for args in test_args:
            matrix.append((command, *args))
    return matrix


# TODO: Some tests are very similar to the ones in multiselect_test.py -> maybe we can refactor them and share even more
class ButtonGroupCommandTests(DeltaGeneratorTestCase):
    @parameterized.expand(
        [
            (
                st.feedback,
                ("thumbs",),
                [":material/thumb_up:", ":material/thumb_down:"],
                "content_icon",
                ButtonGroupProto.Style.NORMAL,
                False,
            ),
            (
                st.pills,
                ("label", ["a", "b", "c"]),
                ["a", "b", "c"],
                "content",
                ButtonGroupProto.Style.PILLS,
                True,
            ),
            (
                lambda *args, **kwargs: ButtonGroupMixin._internal_button_group(
                    st._main, *args, **kwargs
                ),
                (["a", "b", "c"],),
                ["a", "b", "c"],
                "content",
                ButtonGroupProto.Style.NORMAL,
                False,
            ),
        ]
    )
    def test_proto_population(
        self,
        command: Callable[..., None],
        command_args: tuple[Any, ...],
        expected_options: list[str],
        option_field: str,
        style: ButtonGroupProto.Style,
        test_label: bool,
    ):
        command(*command_args)

        delta = self.get_delta_from_queue().new_element.button_group
        assert [
            getattr(option, option_field) for option in delta.options
        ] == expected_options
        assert delta.default == []
        assert delta.click_mode == ButtonGroupProto.ClickMode.SINGLE_SELECT
        assert delta.disabled is False
        assert delta.form_id == ""
        assert (
            delta.selection_visualization
            == ButtonGroupProto.SelectionVisualization.ONLY_SELECTED
        )
        assert delta.style == style

        if test_label:
            assert delta.label == command_args[0]
        assert (
            delta.label_visibility.value
            is LabelVisibilityMessage.LabelVisibilityOptions.VISIBLE
        )

    @parameterized.expand(
        [
            (st.feedback, ("thumbs",)),
            (st.pills, ("label", ["a", "b", "c"])),
            (st.pills, ("label", ["a", "b", "c"]), {"default": "b"}, "b"),
        ]
    )
    def test_default_return_value(
        self,
        command: Callable[..., None],
        command_args: tuple[Any, ...],
        command_kwargs: dict | None = None,
        expected_default: str | None = None,
    ):
        if command_kwargs is None:
            command_kwargs = {}
        res = command(*command_args, **command_kwargs)
        assert res is expected_default

    @parameterized.expand(
        [
            (st.feedback, ("thumbs",)),
            (st.pills, ("label", ["a", "b", "c"])),
        ]
    )
    def test_disabled(self, command: Callable, command_args: tuple[Any, ...]):
        command(*command_args, disabled=True)

        delta = self.get_delta_from_queue().new_element.button_group
        assert delta.disabled is True

    @parameterized.expand(
        get_command_matrix(
            [
                ((),),
                ([],),
                (np.array([]),),
                (pd.Series(np.array([])),),
                (set(),),
            ]
        )
    )
    def test_no_options(self, command: Callable[..., None], options: Any):
        """Test that it handles no options."""
        command(options)

        c = self.get_delta_from_queue().new_element.button_group
        assert c.default[:] == []
        assert [option.content for option in c.options] == []

    @parameterized.expand(
        get_command_matrix(
            [
                (("m", "f"), ["m", "f"]),
                (["male", "female"], ["male", "female"]),
                (np.array(["m", "f"]), ["m", "f"]),
                (pd.Series(np.array(["male", "female"])), ["male", "female"]),
                (pd.DataFrame({"options": ["male", "female"]}), ["male", "female"]),
                (
                    pd.DataFrame(
                        data=[[1, 4, 7], [2, 5, 8], [3, 6, 9]], columns=["a", "b", "c"]
                    ).columns,
                    ["a", "b", "c"],
                ),
            ]
        )
    )
    def test_various_option_types(
        self,
        command: Callable[..., None],
        options: Any,
        proto_options: list[str],
    ):
        """Test that it supports different types of options."""
        command(options)

        c = self.get_delta_from_queue().new_element.button_group
        assert c.default[:] == []
        assert [option.content for option in c.options] == proto_options

    @parameterized.expand(
        get_command_matrix(
            [
                (
                    pd.Series(np.array(["green", "blue", "red", "yellow", "brown"])),
                    ["yellow"],
                    ["green", "blue", "red", "yellow", "brown"],
                    [3],
                ),
                (
                    np.array(["green", "blue", "red", "yellow", "brown"]),
                    ["green", "red"],
                    ["green", "blue", "red", "yellow", "brown"],
                    [0, 2],
                ),
                (
                    ("green", "blue", "red", "yellow", "brown"),
                    ["blue"],
                    ["green", "blue", "red", "yellow", "brown"],
                    [1],
                ),
                (
                    ["green", "blue", "red", "yellow", "brown"],
                    ["brown"],
                    ["green", "blue", "red", "yellow", "brown"],
                    [4],
                ),
                (
                    pd.DataFrame({"col1": ["male", "female"], "col2": ["15", "10"]}),
                    ["male", "female"],
                    ["male", "female"],
                    [0, 1],
                ),
            ]
        )
    )
    def test_various_option_types_with_defaults(
        self,
        command: Callable[..., None],
        options: Any,
        defaults: Any,
        proto_options: list[str],
        expected_defaults: list[int],
    ):
        """Test that it supports different types of options and works with defaults."""
        command(options, default=defaults, selection_mode="multiselect")

        c = self.get_delta_from_queue().new_element.button_group
        assert [option.content for option in c.options] == proto_options
        assert c.default[:] == expected_defaults

    @parameterized.expand(
        get_command_matrix(
            [
                (("Tea", "Water"), [1, 2]),
                # the lambda returns a generator that needs to be fresh
                # for every test run:
                (lambda: (i for i in ("Tea", "Water")), [1, 2]),
                (np.array(["Coffee", "Tea"]), [0, 1]),
                (pd.Series(np.array(["Coffee", "Tea"])), [0, 1]),
                ("Coffee", [0]),
            ]
        )
    )
    def test_default_types(
        self, command: Callable[..., None], defaults: Any, expected: list[Any]
    ):
        if callable(defaults):
            defaults = defaults()

        command(
            ["Coffee", "Tea", "Water"], default=defaults, selection_mode="multiselect"
        )

        c = self.get_delta_from_queue().new_element.button_group
        assert c.default[:] == expected
        assert [option.content for option in c.options] == ["Coffee", "Tea", "Water"]

    @parameterized.expand(
        get_command_matrix([(None, []), ([], []), (["Tea", "Water"], [1, 2])])
    )
    def test_defaults_for_multiselect(
        self, command: Callable[..., None], defaults: Any, expected: list[Any]
    ):
        """Test that valid default can be passed as expected."""
        command(
            ["Coffee", "Tea", "Water"],
            default=defaults,
            selection_mode="multiselect",
        )
        c = self.get_delta_from_queue().new_element.button_group
        assert c.default[:] == expected
        assert [option.content for option in c.options] == ["Coffee", "Tea", "Water"]

    @parameterized.expand(
        get_command_matrix([(None, []), ([], []), (["Tea"], [1]), ("Coffee", [0])])
    )
    def test_default_for_singleselect(
        self, command: Callable[..., None], defaults: Any, expected: list[Any]
    ):
        """Test that valid default can be passed as expected."""
        command(
            ["Coffee", "Tea", "Water"],
            default=defaults,
            selection_mode="select",
        )
        c = self.get_delta_from_queue().new_element.button_group
        assert c.default[:] == expected
        assert [option.content for option in c.options] == ["Coffee", "Tea", "Water"]

    @parameterized.expand(get_command_matrix([]))
    def test_default_for_single_select_must_be_single_value(
        self, command: Callable[..., None]
    ):
        """Test that passing multiple values as default for single select raises an
        exception."""
        with pytest.raises(StreamlitAPIException) as exception:
            command(
                ["Coffee", "Tea", "Water"],
                default=["Coffee", "Tea"],
                selection_mode="select",
            )
        assert (
            str(exception.value)
            == "The default argument to `st.button_group` must be a single value when "
            "`selection_mode='select'`."
        )

    @parameterized.expand(
        get_command_matrix(
            [
                (["Tea", "Vodka", None], StreamlitAPIException),
                ([1, 2], StreamlitAPIException),
            ]
        )
    )
    def test_invalid_defaults(
        self, command: Callable[..., None], defaults: list, expected: type[Exception]
    ):
        """Test that invalid default trigger the expected exception."""
        with pytest.raises(expected):
            command(["Coffee", "Tea", "Water"], default=defaults)

    @parameterized.expand(get_command_matrix([]))
    def test_format_func_is_applied(
        self,
        command: Callable[..., None],
    ):
        """Test that format_func is applied to the options."""
        options = [1, 2, 3]
        command(options, format_func=lambda x: f"{x}!")
        c = self.get_delta_from_queue().new_element.button_group
        for index, option in enumerate(options):
            assert c.options[index].content == f"{option}!"

    @parameterized.expand(
        [
            (st.feedback, ("thumbs",)),
            (st.pills, ("label", ["a", "b", "c"])),
        ]
    )
    def test_on_change_is_registered(
        self,
        command: Callable[..., None],
        command_args: tuple[str, ...],
    ):
        command(*command_args, on_change=lambda x: x)

        ctx = get_script_run_ctx()
        assert ctx is not None
        session_state = ctx.session_state._state
        widget_id = session_state.get_widget_states()[0].id
        metadata = session_state._new_widget_state.widget_metadata.get(widget_id)
        assert metadata is not None
        assert metadata.callback is not None

    @parameterized.expand(get_command_matrix([]))
    def test_pass_icons(self, command: Callable[..., None]):
        command(["Coffee", "Tea"], icons=["☕", "🍵"])

        c = self.get_delta_from_queue().new_element.button_group
        assert c.default == []
        assert [option.content for option in c.options] == ["Coffee", "Tea"]
        assert [option.content_icon for option in c.options] == ["☕", "🍵"]

    @parameterized.expand(get_command_matrix([]))
    def test_icon_list_too_small(self, command: Callable[..., None]):
        """Test that it throws an exception if the icon list is too small."""
        with pytest.raises(StreamlitAPIException) as exception:
            command(["Coffee", "Tea"], icons=["🍵"])
        assert (
            str(exception.value)
            == "The number of icons must match the number of options."
        )

    @parameterized.expand(get_command_matrix([]))
    def test_options_list_too_small_when_icons_provided(
        self, command: Callable[..., None]
    ):
        """Test that it throws an exception if the options list is too small when icons
        are provided."""
        with pytest.raises(StreamlitAPIException) as exception:
            command(
                ["Coffee"],
                icons=[":material/thumb_up:", ":material/thumb_down:"],
            )
        assert (
            str(exception.value)
            == "The number of icons must match the number of options."
        )

    @parameterized.expand(get_command_matrix([], with_st_feedback=True))
    def test_outside_form(self, command: Callable[..., None]):
        """Test that form id is marshalled correctly outside of a form."""
        # pass an option that is valid for st.feedback and also the other button_group
        # commands
        command("thumbs")

        proto = self.get_delta_from_queue().new_element.button_group
        assert proto.form_id == ""

    @parameterized.expand(get_command_matrix([], with_st_feedback=True))
    @patch("streamlit.runtime.Runtime.exists", MagicMock(return_value=True))
    def test_inside_form(self, command: Callable[..., None]):
        """Test that form id is marshalled correctly inside of a form."""

        with st.form("form"):
            # pass an option that is valid for st.feedback and also the other button_group
            # commands
            command("thumbs")

        # 2 elements will be created: form block, widget
        assert len(self.get_all_deltas_from_queue()) == 2

        form_proto = self.get_delta_from_queue(0).add_block
        proto = self.get_delta_from_queue(1).new_element.button_group
        assert proto.form_id == form_proto.form.form_id

    @parameterized.expand(get_command_matrix([]))
    def test_inside_column(self, command: Callable[..., None]):
        """Test that button group commands work correctly inside of a column."""

        col1, _ = st.columns(2)

        with col1:
            command(["bar", "baz"])
        all_deltas = self.get_all_deltas_from_queue()

        # 4 elements will be created: 1 horizontal block, 2 columns, 1 widget
        assert len(all_deltas) == 4
        proto = self.get_delta_from_queue().new_element.button_group

        assert proto.default == []
        assert [option.content for option in proto.options] == ["bar", "baz"]

    def test_inside_column_feedback(self):
        """Test that st.feedback works correctly inside of a column."""

        col1, _ = st.columns(2)

        with col1:
            st.feedback("thumbs")
        all_deltas = self.get_all_deltas_from_queue()

        # 4 elements will be created: 1 horizontal block, 2 columns, 1 widget
        assert len(all_deltas) == 4
        proto = self.get_delta_from_queue().new_element.button_group

        assert proto.default == []
        assert [option.content_icon for option in proto.options] == [
            ":material/thumb_up:",
            ":material/thumb_down:",
        ]

    @parameterized.expand(get_command_matrix([]))
    def test_default_string(self, command: Callable[..., None]):
        """Test if works when the default value is not a list."""
        arg_options = ["some str", 123, None, {}]
        proto_options = ["some str", "123", "None", "{}"]

        command(
            arg_options,
            default="some str",
        )

        c = self.get_delta_from_queue().new_element.button_group
        self.assertListEqual(c.default[:], [0])
        self.assertEqual(
            [option.content for option in c.options],
            proto_options,
        )
