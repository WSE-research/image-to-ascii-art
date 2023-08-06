import streamlit as st
from streamlit.components.v1 import html

from PIL import Image
import base64
import logging
from util import include_css
import subprocess
from datetime import datetime
import os
from decouple import config
from ansi2html import Ansi2HTMLConverter
import math
import imgkit
from ascii_magic import AsciiArt, Back

UPLOAD_DIRECTORY = config('UPLOAD_DIRECTORY')
EXPORT_IMAGE_ENDING = "-ascii-art.png"

width = 60
MIN_WIDTH = 10
MAX_WIDTH = 300

PAGE_ICON = config('PAGE_ICON')
PAGE_IMAGE = config('PAGE_IMAGE')
GITHUB_REPO = config('GITHUB_REPO')
DESCRIPTION = config('DESCRIPTION').replace("\\n", "\n") % (GITHUB_REPO,)
ALLOWED_UPLOAD_TYPES = ["jpg", "jpeg", "png", "bmp", "webp", "gif", "tiff"]
agree_on_showing_additional_information = True

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

conv = Ansi2HTMLConverter()

ascii_image_converter_with_colors = "With colors (I)"
ascii_image_converter_with_colors_complex = "With colors (II)"
ascii_magic_with_colors = "With colors (III)"

ascii_image_converter_with_background_colors = "With background (I)"
ascii_image_converter_with_background_colors_complex = "With background (II)"
ascii_image_converter_only_background_color = "Only background"

ascii_image_converter_neutral = "No colors (I)"
ascii_image_converter_neutral_complex = "No colors (II)"
ascii_magic_neutral = "No colors (III)"

approaches = {
    ascii_image_converter_with_colors: {
        "color": True,
        "description": "ascii-image-converter: with simple, colored ASCII characters"
    },
    ascii_image_converter_with_colors_complex: {
        "color": True,
        "description": "ascii-image-converter: with complex, colored ASCII characters"
    },
    ascii_magic_with_colors: {
        "color": True,
        "description": "ascii_magic: with simple, colored ASCII characters"
    },
    
    ascii_image_converter_with_background_colors: {
        "color": True,
        "description": "ascii-image-converter: with simple, one-colored ASCII characters and background colors"
    },
    ascii_image_converter_with_background_colors_complex: {
        "color": True,
        "description": "ascii-image-converter: with complex, one-colored ASCII characters and background colors"
    },
    ascii_image_converter_only_background_color: {
        "color": True,
        "description": "ascii-image-converter: with background colors only (each character is a whitespace)"
    },

    ascii_image_converter_neutral: {
        "color": False,
        "description": "ascii-image-converter: with simple, one-color ASCII characters"
    },
    ascii_image_converter_neutral_complex: {
        "color": False,
        "description": "ascii-image-converter: with complex, one-color ASCII characters"
    },
    ascii_magic_neutral: {
        "color": False,
        "description": "ascii_magic: with simple, one-color ASCII characters"
    }
}

st.set_page_config(layout="wide", initial_sidebar_state="expanded",
                   page_title="Web UI for ascii-image-converter",
                   page_icon=Image.open(PAGE_ICON)
                   )
include_css(st, ["css/stFileUploadDropzone.css", "css/style_github_ribbon.css",
            "css/style_menu_logo.css", "css/style_logo.css"])  


with st.sidebar:
    with open(PAGE_IMAGE, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
        st.sidebar.markdown(
            f"""
            <div style="display:table;margin-top:-10%;margin-bottom:15%;text-align:center">
                <a href="{GITHUB_REPO}" title="go to GitHub repository"><img src="data:image/png;base64,{image_data}" style="width:66%;"></a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    label = "Define the number of ASCII characters per line in the generated output"
    st.sidebar.markdown("**Parameters**: " + label)
    width = st.slider(label, MIN_WIDTH, MAX_WIDTH, value=width, step=10, label_visibility="collapsed")

    st.sidebar.markdown("**Available approaches:** Activate the approaches you want to use.")
    for approach in approaches.keys():
        approaches[approach]["active"] = st.checkbox(approach, value=True, help=approaches[approach]["description"])

    st.sidebar.markdown("**Visualization:** Activate to focus on the ASCII art generator.")
    agree_on_showing_additional_information = not st.checkbox(
        'minimize layout', value=(not agree_on_showing_additional_information))


# introduce the tool
page_header = """### Image to ASCII art converter

{}                    
""".format(DESCRIPTION)

# show the page header only if the user is not minimizing the layout
if agree_on_showing_additional_information:
    with st.container():
        st.markdown(page_header, unsafe_allow_html=True)
else:
    include_css(st, ["css/remove_space_around_streamlit_body.css"])

label = "Upload an Image file"
st.markdown("#### " + label)
uploaded_image_file = st.file_uploader(
    label, accept_multiple_files=False, label_visibility="collapsed", type=ALLOWED_UPLOAD_TYPES)


@st.cache_resource
def convert_image_to_ascii_art_execute(image_filename, parameters):
    command = ["ascii-image-converter"] + parameters + [image_filename]
    logging.info("execute: " + " ".join(command))
    return subprocess.run(command, capture_output=True)


@st.cache_data
def render_ascii_art_as_html_image(ascii_art, image_base_filename, width, original_image_size):
    image_filename = image_base_filename + "--rendered-html.png"
    html_output = conv.convert(
        ascii_art, full=True, ensure_trailing_newline=False).strip()
    new_style = """
    <style>
    body {
        margin: 0 !important;
        background-color: #FF0 !important;
        line-height: 1.23 !important;
    }
    .ansi2html-content {
        background-color: #000000 !important;
    }
    
    pre {
        white-space: pre !important;
    }
    </style>
    """
    html_output = html_output.replace("<body", new_style + "<body")
    html_output = html_output.replace("""</span>

</pre>""", """</span></pre>""")  # HACK to fix the last line problem
    html_output = html_output.replace("""

</pre>""", """</pre>""")  # HACK to fix the last line problem
    html_filename = image_filename + ".html"
    with open(html_filename, "w") as file:
        file.write(html_output)

    # calculate the correct width for the HTML rendering
    pixels_width = 8 * width - math.floor(width / 5)
    options = {'width': pixels_width}
    imgkit_response = imgkit.from_string(html_output, image_filename, options=options)
    logging.debug("imgkit_response: " + str(imgkit_response))
    return image_filename


# @st.cache_data
def convert_image_to_ascii_art(input_filename, image_filename, parameters, width, original_image_size):
    # convert to ascii text
    parameters = parameters + ["--width", str(width)]
    ascii_art = convert_image_to_ascii_art_execute(input_filename, parameters)

    # convert to ascii image
    export_filename = image_filename + "_width_" + \
        str(width) + EXPORT_IMAGE_ENDING

    export_filename = render_ascii_art_as_html_image(
        ascii_art.stdout.decode("utf-8"), export_filename, width, original_image_size)

    return ascii_art.stdout.decode("utf-8"), export_filename


def convert_image_to_ascii_art_asciiartlib(input_filename, image_filename, width, original_image_size, monochrome):
    art = AsciiArt.from_image(input_filename)
    ascii_art = art.to_ascii(columns=width, monochrome=monochrome)

    export_filename = image_filename + "_width_" + \
        str(width) + EXPORT_IMAGE_ENDING
    export_filename = render_ascii_art_as_html_image(
        ascii_art, export_filename, width, original_image_size)

    return ascii_art, export_filename


def remove_all_characters_from_ascii_art(ascii_art, filename, width, original_image_size):
    ascii_art = ascii_art.replace("*", " ")
    ascii_art = ascii_art.replace("#", " ")
    ascii_art = ascii_art.replace("+", " ")
    ascii_art = ascii_art.replace("=", " ")
    ascii_art = ascii_art.replace("%", " ")
    ascii_art = ascii_art.replace("@", " ")
    ascii_art = ascii_art.replace(".", " ")
    ascii_art = ascii_art.replace("-", " ")
    ascii_art = ascii_art.replace(":", " ")
    filename = filename + "--only-background-color"
    output_filename = render_ascii_art_as_html_image(
        ascii_art, filename, width=width, original_image_size=original_image_size)
    return ascii_art, output_filename


def render_svg(svg_filename):
    """Renders the given svg string."""
    svg = open(svg_filename, 'r').read()
    b64 = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
    html = r'<img src="data:image/svg+xml;base64,%s"/>' % b64
    st.write(html, unsafe_allow_html=True)

@st.cache_data
def get_new_working_dir(upload_filename):
    new_working_directory = UPLOAD_DIRECTORY + "/" + \
        datetime.now().strftime("%Y%m%d-%H%M%S")
    logging.warning(f"new working directory: {new_working_directory}")
    return new_working_directory


# @st.cache_data # TODO set key to input_filename
def save_uploaded_file(input_filename, uploaded_image_file):
    uploaded_image = Image.open(uploaded_image_file)
    uploaded_image.save(input_filename)
    width = uploaded_image.size[0]
    height = uploaded_image.size[1]
    logging.info("uploaded file to " + input_filename)
    return {"width": width, "height": height}


def show_download_buttons(ascii_data, ascii_image_filename, output_filename):
    download_data, download_image, rest = st.columns([1,1,1])
    
    with download_data:
        st.download_button(
            label=":ab: Download ASCII **data** file",
            data=ascii_data,
            file_name='banner.txt',
            mime='text/plain'
        )

    with download_image:
        st.download_button(
            label=":frame_with_picture: Download ASCII **image** file",
            data=open(ascii_image_filename, 'rb').read(),
            file_name=output_filename,
            mime="image/png",
        )


if uploaded_image_file is not None:
    # put everything into one new and unique directory
    current_directory = get_new_working_dir(uploaded_image_file.name)
    try:  # TODO: check first
        os.makedirs(current_directory)
    except:
        pass
    
    input_filename = current_directory + "/export.png"
    input_filename_with_colors = current_directory + "/export-with-colors.png"

    image_size = save_uploaded_file(input_filename, uploaded_image_file)

    input_filename_no_colors = current_directory + "/export-no-colors.png"
    # --complex
    input_filename_with_colors_complex = current_directory + \
        "/export-with-colors-complex.png"
    input_filename_no_colors_complex = current_directory + \
        "/export-no-colors-complex.png"
    # --color-bg
    input_filename_with_colors_colorbg = current_directory + \
        "/export-with-colors-colorbg.png"
    input_filename_with_colors_colorbg_complex = current_directory + \
        "/export-with-colors-colorbg-complex.png"

    asciiartlib_with_colors_input_filename = current_directory + \
        "/export-with-colors-asciiartlib.png"

    asciiartlib_no_colors_input_filename = current_directory + \
        "/export-no-colors-asciiartlib.png"

    active_ascii_generators = []
    for approach in approaches:
        if approaches[approach]["active"]:
            active_ascii_generators.append(approach)
            
    # dynamically generate the tabs for the selected approaches
    tabs = st.tabs(active_ascii_generators)
    
    for i,tab in enumerate(tabs):
        current_approach = active_ascii_generators[i]
        with tab:
            if current_approach == ascii_image_converter_with_colors:
                # convert the image to ascii text and ascii image WITH COLORS
                ascii_art, filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors, ["--color"], width=width, original_image_size=image_size)     
                filename_download = f"ascii-image-with-colors-{width}.png"
            elif current_approach == ascii_image_converter_neutral:
                # convert the image to ascii text and ascii image NO COLORS
                ascii_art, filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_no_colors, [], width=width, original_image_size=image_size) 
                filename_download = f"ascii-image-no-colors-{width}.png"        
            elif current_approach == ascii_image_converter_with_colors_complex:
                # convert the image to ascii text and ascii image WITH COLORS and COMPLEX characters
                ascii_art, filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors_complex, ["--color", "--complex"], width=width, original_image_size=image_size)
                filename_download = f"ascii-image-with-colors-complex-{width}.png"
            elif current_approach == ascii_image_converter_neutral_complex:
                # convert the image to ascii text and ascii image NO COLORS and COMPLEX characters
                ascii_art, filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_no_colors_complex, ["--complex"], width=width, original_image_size=image_size)
                filename_download = f"ascii-image-no-colors-complex-{width}.png"
            elif current_approach == ascii_image_converter_with_background_colors:
                # convert the image to ascii text and ascii image WITH COLORS and COLOR BG
                ascii_art, filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors_colorbg, ["--color", "--color-bg"], width=width, original_image_size=image_size)
                filename_download = f"ascii-image-with-colors-color-bg-{width}.png"
            elif current_approach == ascii_image_converter_with_background_colors_complex:
                # convert the image to ascii text and ascii image WITH COLORS and COLOR BG
                ascii_art, filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors_colorbg_complex, ["--color", "--color-bg", "--complex"], width=width, original_image_size=image_size)
                filename_download = f"ascii-image-with-colors-colorbg-complex-{width}.png"
            elif current_approach == ascii_image_converter_only_background_color:
                # convert the image to ascii text and ascii image with COLOR BG but remove all characters
                ascii_art_original, filename_ascii_art_original = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors_colorbg, ["--color", "--color-bg"], width=width, original_image_size=image_size)
                ascii_art, filename_ascii_art = remove_all_characters_from_ascii_art(
                    ascii_art_original, filename_ascii_art_original, width=width, original_image_size=image_size)
                filename_download = f"ascii-image-with-colors-colorbg-only-background-{width}.png"
            elif current_approach == ascii_magic_with_colors:
                # convert the image to ascii text and ascii image WITH COLORS
                ascii_art, filename_ascii_art = convert_image_to_ascii_art_asciiartlib(
                    input_filename, asciiartlib_with_colors_input_filename, width=width, original_image_size=image_size, monochrome=False)                
                filename_download = f"ascii-image-with-colors-ascii-magic-{width}.png"
            elif current_approach == ascii_magic_neutral:
                # convert the image to ascii text and ascii image NO COLORS
                ascii_art, filename_ascii_art = convert_image_to_ascii_art_asciiartlib(
                    input_filename, asciiartlib_no_colors_input_filename, width=width, original_image_size=image_size, monochrome=True)         
                filename_download = f"ascii-image-no-colors-ascii-magic-{width}.png"
            else:
                st.text("not implemented yet")

            # show the ascii art and download buttons in all tabs
            show_download_buttons(
                ascii_art, filename_ascii_art, filename_download)
            st.image(filename_ascii_art, use_column_width="auto")


st.markdown("""
---
Brought to you by the [<img style="height:3ex;border:0" src="https://avatars.githubusercontent.com/u/120292474?s=96&v=4"> WSE research group](http://wse.technology/) at the [Leipzig University of Applied Sciences](https://www.htwk-leipzig.de/).

See our [GitHub team page](http://wse.technology/) for more projects and tools.
""", unsafe_allow_html=True)

with open("js/change_menu.js", "r") as f:
    javascript = f.read()
    html(f"<script style='display:none'>{javascript}</script>")

html("""
<script>
parent.window.document.querySelectorAll("section[data-testid='stFileUploadDropzone']").forEach(function(element) {
    element.classList.add("fileDropHover")   
});

github_ribbon = parent.window.document.createElement("div");            
github_ribbon.innerHTML = '<a id="github-fork-ribbon" class="github-fork-ribbon right-bottom" href="%s" target="_blank" data-ribbon="Fork me on GitHub" title="Fork me on GitHub">Fork me on GitHub</a>';
if (parent.window.document.getElementById("github-fork-ribbon") == null) {
    parent.window.document.body.appendChild(github_ribbon.firstChild);
}
</script>
""" % (GITHUB_REPO,))
