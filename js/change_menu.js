/**
 * helper to wait for an element to be available in the DOM.
 * 
 * @param {*} selector 
 * @returns 
 */
function waitForElm(selector) {
    parent.window.console.log("waitForElm(" + selector + ")")
    return new Promise(resolve => {
        if (parent.window.document.querySelector(selector)) {
            return resolve(window.document.querySelector(selector));
        }

        const observer = new MutationObserver(mutations => {
            if (parent.window.document.querySelector(selector)) {
                resolve(parent.window.document.querySelector(selector));
                observer.disconnect();
            }
        });

        observer.observe(parent.window.document.body, {
            childList: true,
            subtree: true
        });
    });
}

/**
 * replace the Streamlit menu by a link to the WSE website.
 */
waitForElm('#MainMenu').then((elm) => {
    parent.window.console.log('Element is ready');
    if (parent.window.document.getElementById("WSElogo") == null) {
        let new_logo = parent.window.document.getElementById("MainMenu").parentElement.appendChild(parent.window.document.createElement("span"));
        new_logo.innerHTML = `
        <a href="http://wse.technology?utm_source=menu" title="Brought to you by the WSE research group at the Leipzig University of Applied Sciences. See our GitHub team page for more projects and tools." target="_blank">
        <img id="WSElogo" src='https://avatars.githubusercontent.com/u/120292474?s=96&v=4'>
        </a>
        `;
    }
});