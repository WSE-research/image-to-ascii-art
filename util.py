from PIL import Image
import requests
import logging

def include_css(st, filenames):
    content = ""
    for filename in filenames:
        with open(filename) as f:
            content += f.read()
    st.markdown(f"<style>{content}</style>", unsafe_allow_html=True)

def get_size_of_image(pil_image):
    height = pil_image.size[1]
    width = pil_image.size[0]
    return {"width": width, "height": height}

def download_image(url, download_filename):
    im = Image.open(requests.get(url, stream=True).raw)
    im.save(download_filename)
    logging.info(f"downloaded file from {url} to {download_filename}")
    return get_size_of_image(im)

def save_uploaded_file(input_filename, uploaded_image_file):
    uploaded_image = Image.open(uploaded_image_file)
    uploaded_image.save(input_filename)
    logging.info("uploaded file to " + input_filename)
    return get_size_of_image(uploaded_image)
