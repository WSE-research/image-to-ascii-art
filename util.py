from PIL import Image
import requests
import logging
import os
import re
import base64

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

def copy_file(src, dest):
    with open(src, 'r') as f:
        data = f.read()
        f.close()
        with open(dest, 'w') as f:
            f.write(data)
            f.close()

def replace_values_in_index_html(st, activate, new_title, new_meta_description=None, new_noscript_content=None, canonical_url=None, page_icon_with_path=None, additional_html_head_content=None):
    """
        This method replaces values in the index.html file of the Streamlit package.
        The intention is to change the title of the page, the favicon and the meta description.
    """

    if not activate:
        return

    index_html = os.path.dirname(st.__file__) + '/static/index.html'
    index_html_backup = index_html + ".backup"
    index_html_change_indicator_file = index_html + ".changed"

    # stop if index.html has already been changed
    if os.path.exists(index_html_change_indicator_file):
        return
    else:
        # make a backup of the index.html file
        if not os.path.exists(index_html_backup):
            copy_file(index_html, index_html_backup)
            logging.warning("Created a backup of the " +
                            index_html + " at " + index_html_backup + ".")
        else:
            logging.warning("Backup of the  " + index_html +
                            " already exists at " + index_html_backup + ".")

    logging.warning("Replacing values in index.html. Thereafter, the index.html file will be overwritten. Don't do this on a system where multiple Streamlit applications are using the same Streamlit package.")

    # only replace favicon if it is not None
    if page_icon_with_path is not None:
        with open(page_icon_with_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
            favicon_base64 = "data:image/png;base64," + \
                encoded_string.decode('utf-8')

    # only set canonical_url if it is not None
    if canonical_url is not None and canonical_url != "":
        canonical_url = f'<link rel="canonical" href="{canonical_url}"/>'
    else:
        canonical_url = ""

    # only set new_meta_description if it is not None
    if new_meta_description is not None and new_meta_description != "":
        new_meta_description = f'<meta name="description" content="{new_meta_description}"/>'
    else:
        new_meta_description = ""

    with open(index_html, 'r') as f:
        data = f.read()
        f.close()

        newdata = re.sub('<title>Streamlit</title>',
                         f"<title>{new_title}</title>{new_meta_description}{canonical_url}", data)

        if new_noscript_content is not None and new_noscript_content != "":
            newdata = re.sub('<noscript>You need to enable JavaScript to run this app.</noscript>',
                             f'<noscript>{new_noscript_content}</noscript>', newdata)

        if page_icon_with_path is not None:
            # Do not forget to add the favicon variable also as parameter to set_page_config
            newdata = re.sub('./favicon.png', favicon_base64, newdata)
            
        if additional_html_head_content is not None and additional_html_head_content != "":
            newdata = re.sub('</head>', f'{additional_html_head_content}</head>', newdata)

        with open(index_html, 'w') as f:
            f.write(newdata)
            f.close()

        with open(index_html_change_indicator_file, 'w') as f:
            f.write("This file indicates that the index.html file has been changed. If you want to change the values again, please delete this file.")
            f.close()
            logging.info("to enable a new adaption of the index.html file, please delete the file: " +
                         index_html_change_indicator_file)
