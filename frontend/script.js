const API_URL = "https://stem-unexpected-except-cancelled.trycloudflare.com";

const messages = document.getElementById("messages");
const input = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");

const newChatButton =
    document.getElementById("newChatButton");

const themeButton =
    document.getElementById("themeButton");

const pdfInput =
    document.getElementById("pdfInput");

const uploadStatus =
    document.getElementById("uploadStatus");


/* =====================================================
   ADD MESSAGE
===================================================== */

function addMessage(text, type) {

    const message = document.createElement("div");

    message.className =
        "message " + type;

    const content =
        document.createElement("div");

    content.className =
        "message-content";

    content.textContent = text;

    message.appendChild(content);

    messages.appendChild(message);

    messages.scrollTop =
        messages.scrollHeight;
}


/* =====================================================
   SEND MESSAGE
===================================================== */

async function sendMessage() {

    const text =
        input.value.trim();

    if (!text) {
        return;
    }


    // Remove welcome screen
    const welcome =
        document.querySelector(".welcome");

    if (welcome) {
        welcome.remove();
    }


    // Show user message
    addMessage(text, "user");

    input.value = "";

    input.style.height = "auto";


    // Disable button
    sendButton.disabled = true;

    sendButton.textContent = "…";


    try {

        const response =
            await fetch(
                API_URL + "/chat",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        message: text
                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok || data.error) {

            throw new Error(
                data.detail ||
                "Chat request failed"
            );
        }


        addMessage(
            data.response,
            "bot"
        );


    } catch (error) {

        console.error(
            "CHAT ERROR:",
            error
        );

        addMessage(
            "Veltrox AI could not respond. Please make sure Ollama and the FastAPI backend are running.",
            "bot"
        );

    } finally {

        sendButton.disabled = false;

        sendButton.textContent = "➤";
    }
}


/* =====================================================
   SEND BUTTON
===================================================== */

sendButton.addEventListener(
    "click",
    sendMessage
);


/* =====================================================
   ENTER KEY
===================================================== */

input.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();
        }
    }
);


/* =====================================================
   TEXTAREA AUTO RESIZE
===================================================== */

input.addEventListener(
    "input",
    function() {

        input.style.height =
            "auto";

        input.style.height =
            Math.min(
                input.scrollHeight,
                150
            ) + "px";
    }
);


/* =====================================================
   NEW CHAT
===================================================== */

newChatButton.addEventListener(
    "click",
    function() {

        messages.innerHTML = `
            <div class="welcome">

                <div class="welcome-logo">
                    V
                </div>

                <h2>
                    How can I help you today?
                </h2>

                <p>
                    Ask Veltrox AI anything about
                    programming, Generative AI,
                    your resume, or uploaded documents.
                </p>

                <div class="examples">

                    <button class="example">
                        Explain Generative AI
                    </button>

                    <button class="example">
                        What is RAG?
                    </button>

                    <button class="example">
                        Explain Python
                    </button>

                </div>

            </div>
        `;

        attachExampleButtons();
    }
);


/* =====================================================
   EXAMPLE QUESTIONS
===================================================== */

function attachExampleButtons() {

    const examples =
        document.querySelectorAll(
            ".example"
        );

    examples.forEach(
        function(button) {

            button.addEventListener(
                "click",
                function() {

                    input.value =
                        button.textContent.trim();

                    sendMessage();
                }
            );
        }
    );
}

attachExampleButtons();


/* =====================================================
   PDF UPLOAD
===================================================== */

pdfInput.addEventListener(
    "change",
    async function() {

        const file =
            pdfInput.files[0];

        if (!file) {
            return;
        }


        if (
            !file.name
                .toLowerCase()
                .endsWith(".pdf")
        ) {

            uploadStatus.textContent =
                "Please select a PDF file.";

            return;
        }


        uploadStatus.textContent =
            "Uploading PDF and creating embeddings...";


        try {

            const formData =
                new FormData();

            formData.append(
                "file",
                file
            );


            const response =
                await fetch(
                    API_URL + "/upload-pdf",
                    {
                        method: "POST",
                        body: formData
                    }
                );


            const data =
                await response.json();


            if (
                !response.ok ||
                data.error
            ) {

                throw new Error(
                    data.detail ||
                    data.message ||
                    "PDF upload failed"
                );
            }


            uploadStatus.textContent =
                `✅ ${data.filename} uploaded successfully. ${data.chunks} chunks created. You can now ask questions about your resume.`;

        } catch (error) {

            console.error(
                "UPLOAD ERROR:",
                error
            );

            uploadStatus.textContent =
                "❌ PDF upload failed: " +
                error.message;

        } finally {

            pdfInput.value = "";
        }
    }
);


/* =====================================================
   THEME
===================================================== */

themeButton.addEventListener(
    "click",
    function() {

        document.body.classList.toggle(
            "dark"
        );

        if (
            document.body.classList.contains(
                "dark"
            )
        ) {

            themeButton.textContent =
                "☀️ Light";

        } else {

            themeButton.textContent =
                "🌙 Theme";
        }
    }
);