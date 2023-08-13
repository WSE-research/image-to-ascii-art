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

from ansitoimg.render import (
	ansiToHTML,
	ansiToHTMLRender,
	ansiToRender,
	ansiToSVG,
	ansiToSVGRender,
)
import codecs
import lxml.etree


UPLOAD_DIRECTORY = config('UPLOAD_DIRECTORY')
EXPORT_IMAGE_ENDING = "-ascii-art.png"

width = 60
MIN_WIDTH = 10
MAX_WIDTH = 300
RENDER_SCALE_PIXELS = 8

PAGE_ICON = config('PAGE_ICON')
PAGE_IMAGE = config('PAGE_IMAGE')
GITHUB_REPO = config('GITHUB_REPO')
DESCRIPTION = config('DESCRIPTION').replace("\\n", "\n") % (GITHUB_REPO,)
ALLOWED_UPLOAD_TYPES = ["jpg", "jpeg", "png", "bmp", "webp", "gif", "tiff"]
agree_on_showing_additional_information = True
render_scale_pixels = RENDER_SCALE_PIXELS

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
            "css/style_menu_logo.css", "css/style_logo.css", "css/style_ascii_images.css"])  


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

    st.sidebar.markdown("**Download:** It is recommended to disable the PNG option if you want to generate a lot of ASCII art images and re-activate when ready to download.")
    svg_download_activated = st.sidebar.checkbox("Enable download as SVG", value=True)
    png_download_activated = st.sidebar.checkbox("Enable download as PNG", value=False)

    st.sidebar.markdown("**Visualization:** Activate to focus on the ASCII art generator.")
    agree_on_showing_additional_information = not st.checkbox(
        'minimize layout', value=(not agree_on_showing_additional_information))

    label = "render_scale_pixels"
    help = "render_scale_pixels"
    st.sidebar.markdown(label)
    render_scale_pixels = st.sidebar.number_input(label, label_visibility="collapsed", min_value=1, max_value=16, value=render_scale_pixels, help=help)  


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
def render_ascii_art_as_html_image(ascii_art, image_base_filename, width, original_image_size, svg_download_activated, png_download_activated):
    image_filename = image_base_filename + "--rendered-html.png"
    html_output = conv.convert(
        ascii_art, full=True, ensure_trailing_newline=False).strip()
    new_style = """
    <style>
    body {
        margin: 0 !important;
        background-color: #FF0 !important;
        line-height: 1.1 !important;
        font-size: 20px !important;
    }
    .ansi2html-content {
        background-color: #000000 !important;
    }
    
    pre {
        white-space: pre !important;
        font-family: "Courier New" !important;
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

    svg_image_filename = image_filename + ".svg"
    #png_image_filename = image_filename + ".png"
    height = len(ascii_art.strip().split("\n"))
    ansiToSVG(ascii_art, svg_image_filename, width=width, title=f"Preview of {width}x{height} ASCII art as SVG")
    #ansiToRender(ascii_art, png_image_filename, width=width, title=f"Preview of {width}x{height} ASCII art as PNG")
    
    svg_image_filename_optimized = optimize_svg_console_output(svg_image_filename)
    logging.info("svg_image_filename: " + str(svg_image_filename_optimized))

    png_image_filename = None
    if png_download_activated:
        png_image_filename = create_png_image(svg_image_filename_optimized, original_image_size["width"])
        logging.info("png_image_filename: " + str(png_image_filename))
    
    return svg_image_filename_optimized, png_image_filename


def optimize_svg_console_output(svg_filename):
    """
    This function optimizes the SVG file generated by ansiToSVG.
    It is a hacky workaround to remove the console frame around the console content.
    """
    
    # optimize viewbox
    root = lxml.etree.parse(svg_filename)
    viewbox = root.getroot().attrib['viewBox']
    viewbox = viewbox.split(" ")
    viewbox = [float(i) for i in viewbox]

    viewbox[1] = viewbox[1] + 2
    viewbox[2] = viewbox[2] - 19
    viewbox[3] = viewbox[3] - 53
    root.getroot().attrib['viewBox'] = " ".join([str(i) for i in viewbox])

    # move the content to the top left
    all_first_level_children = root.getroot().getchildren()
    all_g_elements = [i for i in all_first_level_children if i.tag == "{http://www.w3.org/2000/svg}g"]
    g0 = all_g_elements[-1]
    g0.attrib['transform'] = "translate(0,0)"

    # remove round buttons (remove all children of g1)
    g1 = all_g_elements[-2]
    for i in g1.getchildren():
        g1.remove(i)    

    # hide the background rectangle
    all_rect_elements = [i for i in all_first_level_children if i.tag == "{http://www.w3.org/2000/svg}rect"]
    rect0 = all_rect_elements[0]
    rect0.attrib['fill-opacity'] = "0.0"

    # hide the text
    all_text_elements = [i for i in all_first_level_children if i.tag == "{http://www.w3.org/2000/svg}text"]
    all_text_elements[0].attrib['fill-opacity'] = "0.0"

    # write the new SVG file
    outfile = svg_filename + "_optimized.svg"
    with codecs.open(outfile, "wb") as out:
        root.write(out)

    return outfile


# @st.cache_data
def convert_image_to_ascii_art(input_filename, image_filename, parameters, width, original_image_size, svg_download_activated, png_download_activated):
    # convert to ascii text
    parameters = parameters + ["--width", str(width)]
    ascii_art = convert_image_to_ascii_art_execute(input_filename, parameters)

    # convert to ascii image
    export_filename = image_filename + "_width_" + \
        str(width) + EXPORT_IMAGE_ENDING

    svg_export_filename, png_export_filename = render_ascii_art_as_html_image(
        ascii_art.stdout.decode("utf-8"), 
        export_filename, 
        width, 
        original_image_size, 
        svg_download_activated, 
        png_download_activated
    )

    return ascii_art.stdout.decode("utf-8"), svg_export_filename, png_export_filename


def convert_image_to_ascii_art_asciiartlib(input_filename, image_filename, width, original_image_size, monochrome, svg_download_activated, png_download_activated):
    art = AsciiArt.from_image(input_filename)
    ascii_art = art.to_ascii(columns=width, monochrome=monochrome)

    export_filename = image_filename + "_width_" + \
        str(width) + EXPORT_IMAGE_ENDING
    svg_export_filename, png_export_filename = render_ascii_art_as_html_image(
        ascii_art, 
        export_filename, 
        width, 
        original_image_size, 
        svg_download_activated, 
        png_download_activated
    )

    return ascii_art, svg_export_filename, png_export_filename


def remove_all_characters_from_ascii_art(ascii_art, filename, width, original_image_size, svg_download_activated, png_download_activated):
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
    svg_export_filename, png_export_filename = render_ascii_art_as_html_image(
        ascii_art, filename, width=width, original_image_size=original_image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated)
    return ascii_art, svg_export_filename, png_export_filename


def render_svg(svg_filename, width, render_scale_pixels):
    """Renders the given SVG string."""
    svg = open(svg_filename, 'r').read()
    b64 = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
    html = r'<img class="svg_ascii_art" src="data:image/svg+xml;base64,%s" width="%spx" />' % (b64, width * render_scale_pixels)
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


#from svglib.svglib import svg2rlg
#from reportlab.graphics import renderPM

def create_png_image(svg_filename, output_width):
    
    return convert_with_inkscape(svg_filename, output_width)
    
    # png_filename = os.path.splitext(svg_filename)[0] + ".png"

    # from cairosvg.surface import PNGSurface
    # with open(svg_filename, 'rb') as svg_file:
    #     PNGSurface.convert(
    #         bytestring=svg_file.read(),
    #         width=output_width,
    #         write_to=open(png_filename, 'wb')
    #     )
    # logging.info("created PNG image " + png_filename)

    # return png_filename


def convert_with_inkscape(svg_filename, output_width):
    png_filename = os.path.splitext(svg_filename)[0] + ".png"
    logging.info("created PNG image " + png_filename)
    try:
        inkscape_path = subprocess.check_output(["which", "inkscape"]).strip()
    except subprocess.CalledProcessError:
        st.error("ERROR: You need inkscape installed to use this script.")
        logging.error("ERROR: You need inkscape installed to use this script.")
        return None

    args = [
        inkscape_path.decode('utf-8'),
        "--without-gui",
        "-f", svg_filename,
        "--export-area-page",
        "-w", str(output_width),
        "--export-png=", png_filename
    ]
    st.info("execute inkscape:\n".join(args))
    
    try:
        result = subprocess.check_call(args, stderr=subprocess.STDOUT)
        return png_filename
    except subprocess.CalledProcessError as e:
        st.error("ERROR: " + str(e))
        logging.error("ERROR: " + str(e))
        return None


def show_download_buttons(ascii_data, svg_filename, svg_download_activated, png_filename, png_download_activated, output_basename):
    download_data, download_svg_image, download_png_image, rest = st.columns([1,1,1,1])
    
    with download_data:
        st.download_button(
            label=":ab: Download ASCII **data** file",
            data=ascii_data,
            file_name='banner.txt',
            mime='text/plain'
        )

    if svg_download_activated and svg_filename is not None:
        with download_svg_image:
            st.download_button(
                label=":frame_with_picture: Download ASCII **SVG image** file",
                data=open(svg_filename, 'rb').read(),
                file_name=output_basename + ".svg",
                mime="image/svg+xml"
            )

    if png_download_activated and png_filename is not None:        
        with download_png_image:
            st.download_button(
                label=":frame_with_picture: Download ASCII **PNG image** file",
                data=open(png_filename, 'rb').read(),
                file_name=output_basename + ".png",
                mime="image/png"
            )


if uploaded_image_file is not None:
    # put everything into one new and unique directory
    current_directory = get_new_working_dir(uploaded_image_file.name)
    
    if not os.path.exists(current_directory):
        os.makedirs(current_directory)
    
    base_filename = current_directory + "/" + os.path.splitext(uploaded_image_file.name)[0]
    input_filename = base_filename + ".png"
    input_filename_with_colors = base_filename + "_with-colors.png" # TODO: normalize filename

    image_size = save_uploaded_file(input_filename, uploaded_image_file)

    input_filename_no_colors = base_filename + "_no-colors.png"
    # --complex
    input_filename_with_colors_complex = base_filename + "_with-colors-complex.png"
    input_filename_no_colors_complex = base_filename + "_no-colors-complex.png"
    # --color-bg
    input_filename_with_colors_colorbg = base_filename + "_with-colors-colorbg.png"
    input_filename_with_colors_colorbg_complex = base_filename + "_with-colors-colorbg-complex.png"

    asciiartlib_with_colors_input_filename = base_filename + "_with-colors-asciiartlib.png"

    asciiartlib_no_colors_input_filename = base_filename + "_no-colors-asciiartlib.png"

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
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors, ["--color"], width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated)
                filename_download = f"ascii-image-with-colors-{width}.png"
            elif current_approach == ascii_image_converter_neutral:
                # convert the image to ascii text and ascii image NO COLORS
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_no_colors, [], width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated)
                filename_download = f"ascii-image-no-colors-{width}.png"        
            elif current_approach == ascii_image_converter_with_colors_complex:
                # convert the image to ascii text and ascii image WITH COLORS and COMPLEX characters
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors_complex, ["--color", "--complex"], width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated)
                filename_download = f"ascii-image-with-colors-complex-{width}.png"
            elif current_approach == ascii_image_converter_neutral_complex:
                # convert the image to ascii text and ascii image NO COLORS and COMPLEX characters
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_no_colors_complex, ["--complex"], width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated)
                filename_download = f"ascii-image-no-colors-complex-{width}.png"
            elif current_approach == ascii_image_converter_with_background_colors:
                # convert the image to ascii text and ascii image WITH COLORS and COLOR BG
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors_colorbg, ["--color", "--color-bg"], width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated)
                filename_download = f"ascii-image-with-colors-color-bg-{width}.png"
            elif current_approach == ascii_image_converter_with_background_colors_complex:
                # convert the image to ascii text and ascii image WITH COLORS and COLOR BG
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors_colorbg_complex, ["--color", "--color-bg", "--complex"], width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated)
                filename_download = f"ascii-image-with-colors-colorbg-complex-{width}.png"
            elif current_approach == ascii_image_converter_only_background_color:
                # convert the image to ascii text and ascii image with COLOR BG but remove all characters
                ascii_art_original, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors_colorbg, ["--color", "--color-bg"], width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated)
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = remove_all_characters_from_ascii_art(
                    ascii_art_original, svg_filename_ascii_art, width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated)
                filename_download = f"ascii-image-with-colors-colorbg-only-background-{width}.png"
            elif current_approach == ascii_magic_with_colors:
                # convert the image to ascii text and ascii image WITH COLORS
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art_asciiartlib(
                    input_filename, asciiartlib_with_colors_input_filename, width=width, original_image_size=image_size, monochrome=False, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated)                
                filename_download = f"ascii-image-with-colors-ascii-magic-{width}.png"
            elif current_approach == ascii_magic_neutral:
                # convert the image to ascii text and ascii image NO COLORS
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art_asciiartlib(
                    input_filename, asciiartlib_no_colors_input_filename, width=width, original_image_size=image_size, monochrome=True, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated)
                filename_download = f"ascii-image-no-colors-ascii-magic-{width}.png"
            else:
                st.text("not implemented yet")

            # show the ascii art and download buttons in all tabs
            show_download_buttons(
                ascii_art, 
                svg_filename=svg_filename_ascii_art, 
                svg_download_activated=svg_download_activated,
                png_filename=png_filename_ascii_art, 
                png_download_activated=png_download_activated,
                output_basename=filename_download
            )
            
            svg_image_col, png_image_col = st.columns([1,1])
            if svg_download_activated and svg_filename_ascii_art is not None:
                with svg_image_col:
                    render_svg(svg_filename_ascii_art, width=width, render_scale_pixels=render_scale_pixels)

            if png_download_activated and png_filename_ascii_art is not None:
                with png_image_col:
                    st.image(png_filename_ascii_art, use_column_width="auto")


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
