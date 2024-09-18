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

import streamlit as st

st.header("Pills - standard")
pills_options = [
    "🧰 General widgets",
    "📊 Charts",
    "🌇 Images",
    "🎥 Video",
    "📝 Text",
    "🗺️ Maps & geospatial",
    "🧮 Dataframes & tables",
    "🧬 Molecules & genes",
    "🪢 Graphs",
    "🧊 3D",
    "✏️ Code & editors",
    "📃 Page navigation",
    "🔐 Authentication",
    "🎨 Style & layout",
    "🛠️ Developer tools",
    "🏗️ App builders",
    "🔌 Integrations with other tools",
    "📦 Collections of components",
]
selection = st.pills(
    "Select some options",
    pills_options,
    key="pills",
    selection_mode="multiselect",
    help="This is for choosing options",
)
st.write(f"Multi selection: {selection}")


st.header("Pills - with icons")
selection = st.pills(
    "Select a single option",
    options=[0, 1, 2, 3],
    icons=[
        ":material/add:",
        ":material/zoom_in:",
        ":material/zoom_out:",
        ":material/zoom_out_map:",
    ],
    format_func=lambda x: "",
    key="icon_only_pills",
    selection_mode="select",
)
st.write(f"Single selection: {selection}")
