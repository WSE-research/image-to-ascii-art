import streamlit as st
from streamlit.components.v1 import html

from PIL import Image
import base64
import logging
import codecs
import subprocess
from datetime import datetime
import time
import lxml.etree
import os
from decouple import config
from ansi2html import Ansi2HTMLConverter
from ascii_magic import AsciiArt
from ansitoimg.render import ansiToSVG
from util import include_css, download_image, save_uploaded_file
import json

UPLOAD_DIRECTORY = config('UPLOAD_DIRECTORY')
EXPORT_IMAGE_ENDING = "-ascii-art.png"
MIN_WIDTH = 10
MAX_WIDTH = 300
RENDER_SCALE_PIXELS = 8
DEFAULT_OUTPUT_WIDTH = 1024
PAGE_ICON = config('PAGE_ICON')
PAGE_IMAGE = config('PAGE_IMAGE')
GITHUB_REPO = config('GITHUB_REPO')
DESCRIPTION = config('DESCRIPTION').replace("\\n", "\n") % (GITHUB_REPO, GITHUB_REPO + "/issues/new", GITHUB_REPO + "/issues/new")
ALLOWED_UPLOAD_TYPES = ["jpg", "jpeg", "png", "bmp", "webp", "gif", "tiff"]

width = 60
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

def update_width_slider():
    st.session_state.width_slider = st.session_state.width_input

def update_width_input():
    st.session_state.width_input = st.session_state.width_slider

st.set_page_config(layout="wide", initial_sidebar_state="expanded",
                   page_title="Web UI for ascii-image-converter",
                   page_icon=Image.open(PAGE_ICON)
                   )
include_css(st, ["css/stFileUploadDropzone.css", "css/style_github_ribbon.css",
            "css/style_menu_logo.css", "css/style_logo.css", "css/style_ascii_images.css", "css/style_tabs.css"])  

SOURCE_UPLOAD = "Upload"
SOURCE_DOWNLOAD = "Download"

with st.sidebar:
    with open(PAGE_IMAGE, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
        st.sidebar.markdown(
            f"""
            <div style="display:table;margin-top:-10%;margin-bottom:15%;text-align:center">
                <a href="{GITHUB_REPO}" title="go to GitHub repository"><img src="data:image/png;base64,{image_data}" class="app_logo"></a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    label = "Select the source of the image"
    help = "Upload: Upload an image from your local computer.\n\nDownload: Download an image from the internet."
    source = st.sidebar.radio(label, [SOURCE_UPLOAD, SOURCE_DOWNLOAD], index=0, key="source", help=help, horizontal=True)

    label = "Define the number of ASCII characters per line in the generated output"
    help="The higher the number, the more detailed the output will be. However, it will also take longer to generate the output."
    st.sidebar.markdown("----\n\n**ASCII line lenght**: " + label)
    width = st.slider(label, MIN_WIDTH, MAX_WIDTH, value=width, step=1, label_visibility="collapsed", help=help, key="width_slider", on_change=update_width_input)
    width = st.number_input(label, min_value=MIN_WIDTH, max_value=MAX_WIDTH, value=width, step=10, key="width_input", help=help, label_visibility="collapsed", on_change=update_width_slider)

    st.sidebar.markdown("----\n\n**Available approaches:** Activate the approaches you want to use.")
    for approach in approaches.keys():
        approaches[approach]["active"] = st.checkbox(approach, value=True, help=approaches[approach]["description"])

    st.sidebar.markdown("----\n**Download:** It is recommended to disable the PNG option if you want to generate a lot of ASCII art images and re-activate when ready to download.")
    
    svg_download_activated = st.sidebar.checkbox("Enable download as SVG", value=True, help="SVG is a vector format and can be scaled without loss of quality.")
    png_download_activated = st.sidebar.checkbox("Enable download as PNG", value=False, help="PNG is a raster format and can not be scaled without loss of quality.")

    if png_download_activated:
        help = "The PNG image will be generated from the SVG image. Hence, it will be of good quality in any case."
        label = "Define the generated PNG image width"
        output_width = st.sidebar.number_input(label, label_visibility="visible", min_value=1, max_value=4096, value=DEFAULT_OUTPUT_WIDTH, help=help)  

    st.sidebar.markdown("----\n**Visualization:**")
    label = "number of pixels per ASCII character"
    help = "The number of pixels per ASCII character in the UI. The higher the value, the more detailed the ASCII art image will be shown in the browser."
    render_scale_pixels = st.sidebar.number_input(label, label_visibility="visible", min_value=1, max_value=16, value=render_scale_pixels, help=help)  

    help = """The background color is just used here, not in the generated ASCII art image. 
    
Hence, it is intended to simulate the background color of the console/website where the ASCII art image will be used.
    
If you want to change the actual background of your ASCII art image, then you should change the background color in uploaded/provided image. 
    """
    transparent_background = st.checkbox('transparent preview background', value=True, help=help)
    if transparent_background:
        background_color = "transparent"
    else:
        background_color = st.color_picker('Pick A Color', '#FFFFFF', help=help)
        st.write('The current color is', background_color," (used for the UI here, not used in the generated ASCII image).")

    help = "Activate to focus on the ASCII art generator. It will remove some white space and text from the UI."
    agree_on_showing_additional_information = not st.checkbox(
        'minimize layout', value=(not agree_on_showing_additional_information), help=help)


@st.cache_data
def get_new_working_dir(upload_filename):
    new_working_directory = UPLOAD_DIRECTORY + "/" + \
        datetime.now().strftime("%Y%m%d-%H%M%S")
    logging.warning(f"new working directory: {new_working_directory}")
    return new_working_directory



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


current_directory = get_new_working_dir(str(time.time()))
if not os.path.exists(current_directory):
    os.makedirs(current_directory)

download_url = None
uploaded_image_file = None
base_filename = None
image_size = None

selection_source, preview_original_image = st.columns([3, 1])

with selection_source:
    if source == SOURCE_UPLOAD:
        label = "Upload an image file"
        help = "If you want to use an image from the internet, then select the 'Download' option in the sidebar."
        st.markdown("#### " + label, help=help)
        uploaded_image_file = st.file_uploader(
            label, accept_multiple_files=False, label_visibility="collapsed", type=ALLOWED_UPLOAD_TYPES)
        uploaded_image_file_name = uploaded_image_file.name if uploaded_image_file else None

        # put everything into one new and unique directory
        if uploaded_image_file_name is not None:
            base_filename = current_directory + "/" + os.path.splitext(uploaded_image_file_name)[0]
            input_filename = base_filename + ".png"
            image_size = save_uploaded_file(input_filename, uploaded_image_file)

    if source == SOURCE_DOWNLOAD:
        label = "Download an image from the Web"
        help = "If you want to use an image from your computer, then select the 'Upload' option in the sidebar."
        st.markdown("#### " + label, help=help)
        download_url = st.text_input("Enter the URL of an image file (allowed file types: %s), e.g., https://avatars.githubusercontent.com/u/120292474" % (", ".join(ALLOWED_UPLOAD_TYPES),), key="url")
        if download_url is not None and download_url.strip() != "":
            base_filename = current_directory + "/downloaded_image"
            input_filename = base_filename + base64.b64encode(download_url.encode("utf-8")).decode("utf-8") + ".png"
            try:
                image_size = download_image(download_filename=input_filename, url=download_url)
                st.info("Downloaded image from %s (size %sx%s)." % (download_url, image_size["width"], image_size["height"]))
            except Exception as e:
                st.error(f"Error while downloading the image from {download_url}: " + str(e))
                download_url = None
                base_filename = None
                input_filename = None
                image_size = None
                
with preview_original_image:
    if image_size is not None:
        label = "Original image (%sx%s)" % (image_size["width"], image_size["height"])
        help = "This is just a preview of the original image."
        st.image(input_filename, label, use_column_width=True)

# @st.cache_resource
def convert_image_to_ascii_art_execute(image_filename, parameters):
    command = ["ascii-image-converter"] + parameters + [image_filename]
    logging.info("execute: " + " ".join(command))
    return subprocess.run(command, capture_output=True)


# @st.cache_data
def render_ascii_art_as_html_image(ascii_art, image_base_filename, width, original_image_size, svg_download_activated, png_download_activated, output_width):
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
    height = len(ascii_art.strip().split("\n"))
    ansiToSVG(ascii_art, svg_image_filename, width=width, title=f"Preview of {width}x{height} ASCII art as SVG")
    
    svg_image_filename_optimized = optimize_svg_console_output(svg_image_filename)
    logging.info("svg_image_filename: " + str(svg_image_filename))
    logging.info("svg_image_filename_optimized: " + str(svg_image_filename_optimized))

    png_image_filename = None
    if png_download_activated:
        png_image_filename = create_png_image(svg_image_filename_optimized, output_width)
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


@st.cache_data
def convert_image_to_ascii_art(input_filename, image_filename, parameters, width, original_image_size, svg_download_activated, png_download_activated, output_width):
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
        png_download_activated,
        output_width=output_width
    )
    
    logging.info("svg_export_filename: " + str(svg_export_filename))
    
    if svg_download_activated and not os.path.isfile(svg_export_filename):
        st.error("SVG file not found: " + str(svg_export_filename))
        logging.error("SVG file not found: " + str(svg_export_filename))
        
    if png_download_activated and not os.path.isfile(png_export_filename):
        st.error("PNG file not found: " + str(png_export_filename))
        logging.error("PNG file not found: " + str(png_export_filename))

    return ascii_art.stdout.decode("utf-8"), svg_export_filename, png_export_filename


def convert_image_to_ascii_art_asciiartlib(input_filename, image_filename, width, original_image_size, monochrome, svg_download_activated, png_download_activated, output_width):
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
        png_download_activated, 
        output_width=output_width
    )

    return ascii_art, svg_export_filename, png_export_filename

@st.cache_data
def remove_all_characters_from_ascii_art(ascii_art, filename, width, original_image_size, svg_download_activated, png_download_activated, output_width):
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
        ascii_art, 
        filename, 
        width=width, 
        original_image_size=original_image_size, 
        svg_download_activated=svg_download_activated, 
        png_download_activated=png_download_activated, 
        output_width=output_width
    )
    return ascii_art, svg_export_filename, png_export_filename


def render_svg(svg_filename, width, render_scale_pixels):
    """Renders the given SVG string."""
    svg = open(svg_filename, 'r').read()
    b64 = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
    html = r'<img title="SVG image" class="svg_ascii_art" src="data:image/svg+xml;base64,%s" width="%spx" /><br><div data-testid="caption">%s with %s characters per line</div>' % (b64, width * render_scale_pixels, "SVG image", width)
    st.write(html, unsafe_allow_html=True)


@st.cache_data
def create_png_image(svg_filename, output_width):
    return convert_with_inkscape(svg_filename, output_width)

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
        "--export-filename", png_filename,
        "-w", str(output_width),
        svg_filename
    ]
    
    try:
        result = subprocess.check_call(args, stderr=subprocess.STDOUT)
        return png_filename
    except subprocess.CalledProcessError as e:
        st.error("ERROR: " + "\n".join(args))
        logging.error("ERROR: " + str(e))
        return None


def show_download_buttons(ascii_data, svg_filename, svg_download_activated, png_filename, png_download_activated, output_basename):
    
    # create a columns layout depending on the number of download buttons
    if svg_download_activated and png_download_activated:
        download_svg_image, download_data, download_png_image = st.columns([1,1,1])
    elif svg_download_activated:
        rest0,download_svg_image,download_data,rest1 = st.columns([1,10,10,1])
    elif png_download_activated:
        rest0, download_data, download_png_image, rest1 = st.columns([1,10,10,1])
    else:
        rest0,download_data,rest1 = st.columns([1,10,1])
        
    if svg_download_activated and svg_filename is not None:
        with download_svg_image:
            st.download_button(
                label=":frame_with_picture: Download ASCII **SVG image** file",
                data=open(svg_filename, 'rb').read(),
                file_name=output_basename + ".svg",
                mime="image/svg+xml"
            )

    with download_data:
        st.download_button(
            label=":ab: Download ASCII **data** file",
            data=ascii_data,
            file_name='banner.txt',
            mime='text/plain',
            key=output_basename + "_plain_ascii_data"
        )

    if png_download_activated and png_filename is not None:        
        with download_png_image:
            st.download_button(
                label=":frame_with_picture: Download ASCII **PNG image** file",
                data=open(png_filename, 'rb').read(),
                file_name=output_basename + ".png",
                mime="image/png",
            )


def save_current_configuration(data, absolute_filename):
    """
    Saves the given configuration data to a file.
    """
    with open(absolute_filename, "w") as f:
        f.write(json.dumps(data, indent=4))

if base_filename is not None and (uploaded_image_file is not None or (download_url is not None and download_url.strip() != "")): # for safety reasons
    
    st.markdown("""<style>
        .stTabs div[data-testid="stVerticalBlock"] div[data-testid="stImage"] img,
        .svg_ascii_art{
            background-color: %s;
        }
        </style>
    """ % background_color, unsafe_allow_html=True)    
    
    if "output_width" not in locals():
        output_width=DEFAULT_OUTPUT_WIDTH

    input_filename_with_colors = base_filename + "_with-colors.png" # TODO: normalize filename

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

    save_current_configuration({
        "base_filename": base_filename,
        "original_image_dimensions": image_size,
        "original_image_size": os.path.getsize(input_filename),
        "active_ascii_generators": active_ascii_generators,
        "svg_download_activated": svg_download_activated,
        "png_download_activated": png_download_activated,
        "characters": width,
        "output_width": output_width,
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": datetime.now().timestamp()
    }, base_filename + "_" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".json")
    
            
    # dynamically generate the tabs for the selected approaches
    tabs = st.tabs(active_ascii_generators)
    
    for i,tab in enumerate(tabs):
        current_approach = active_ascii_generators[i]
        with tab:
            if current_approach == ascii_image_converter_with_colors:
                # convert the image to ascii text and ascii image WITH COLORS
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors, ["--color"], width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated, output_width=output_width)
                filename_download = f"ascii-image-with-colors-{width}.png"
            elif current_approach == ascii_image_converter_neutral:
                # convert the image to ascii text and ascii image NO COLORS
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_no_colors, [], width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated, output_width=output_width)
                filename_download = f"ascii-image-no-colors-{width}.png"        
            elif current_approach == ascii_image_converter_with_colors_complex:
                # convert the image to ascii text and ascii image WITH COLORS and COMPLEX characters
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors_complex, ["--color", "--complex"], width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated, output_width=output_width)
                filename_download = f"ascii-image-with-colors-complex-{width}.png"
            elif current_approach == ascii_image_converter_neutral_complex:
                # convert the image to ascii text and ascii image NO COLORS and COMPLEX characters
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_no_colors_complex, ["--complex"], width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated, output_width=output_width)
                filename_download = f"ascii-image-no-colors-complex-{width}.png"
            elif current_approach == ascii_image_converter_with_background_colors:
                # convert the image to ascii text and ascii image WITH COLORS and COLOR BG
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors_colorbg, ["--color", "--color-bg"], width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated, output_width=output_width)
                filename_download = f"ascii-image-with-colors-color-bg-{width}.png"
            elif current_approach == ascii_image_converter_with_background_colors_complex:
                # convert the image to ascii text and ascii image WITH COLORS and COLOR BG
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors_colorbg_complex, ["--color", "--color-bg", "--complex"], width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated, output_width=output_width)
                filename_download = f"ascii-image-with-colors-colorbg-complex-{width}.png"
            elif current_approach == ascii_image_converter_only_background_color:
                # convert the image to ascii text and ascii image with COLOR BG but remove all characters
                ascii_art_original, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art(
                    input_filename, input_filename_with_colors_colorbg, ["--color", "--color-bg"], width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated, output_width=output_width)
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = remove_all_characters_from_ascii_art(
                    ascii_art_original, svg_filename_ascii_art, width=width, original_image_size=image_size, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated, output_width=output_width)
                filename_download = f"ascii-image-with-colors-colorbg-only-background-{width}.png"
            elif current_approach == ascii_magic_with_colors:
                # convert the image to ascii text and ascii image WITH COLORS
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art_asciiartlib(
                    input_filename, asciiartlib_with_colors_input_filename, width=width, original_image_size=image_size, monochrome=False, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated, output_width=output_width)                
                filename_download = f"ascii-image-with-colors-ascii-magic-{width}.png"
            elif current_approach == ascii_magic_neutral:
                # convert the image to ascii text and ascii image NO COLORS
                ascii_art, svg_filename_ascii_art, png_filename_ascii_art = convert_image_to_ascii_art_asciiartlib(
                    input_filename, asciiartlib_no_colors_input_filename, width=width, original_image_size=image_size, monochrome=True, svg_download_activated=svg_download_activated, png_download_activated=png_download_activated, output_width=output_width)
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
            
            # show the ascii art in the current tab
            svg_image_col = None
            png_image_col = None
            if svg_download_activated and png_download_activated:
                svg_image_col, png_image_col = st.columns([1,1])
            elif svg_download_activated:
                svg_image_col = st.container()
            elif png_download_activated:
                png_image_col = st.container()
            else:
                svg_image_col, png_image_col = st.columns([1,1])

            if svg_download_activated and svg_filename_ascii_art is not None:
                with svg_image_col:
                    render_svg(svg_filename_ascii_art, width=width, render_scale_pixels=render_scale_pixels)

            if png_download_activated and png_filename_ascii_art is not None:
                with png_image_col:
                    st.image(png_filename_ascii_art, use_column_width="auto", width=width, caption=f"PNG image with width {output_width}px")


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
