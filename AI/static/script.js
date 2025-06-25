document.getElementById("uploadForm").addEventListener("submit", function(event) {
    event.preventDefault();
    let formData = new FormData(this);

    document.getElementById("status").innerText = "Processing... please wait.";

    fetch("/translate_pdf", {
        method: "POST",
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        return response.blob();
    })
    .then(blob => {
        let url = window.URL.createObjectURL(blob);
        let a = document.createElement("a");
        a.href = url;
        a.download = "translated.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
        document.getElementById("status").innerText = "Translation complete! Downloading file...";
    })
    .catch(error => {
        console.error("Translation failed:", error);
        document.getElementById("status").innerText = "Error processing translation.";
    });

});
const res = await fetch('/assistant', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message })
});

if (res.redirected || res.status === 302) {
  chatWindow.innerHTML += `<div class="chat-bubble chat-assistant text-danger">Please log in to talk to Genie ✨</div>`;
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return;
}

const data = await res.json();
chatWindow.innerHTML += `<div class="chat-bubble chat-assistant">${data.reply}</div>`;
chatWindow.scrollTop = chatWindow.scrollHeight;
