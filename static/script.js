
const messageBox = document.getElementById("message");
const wordCount = document.getElementById("wordCount");

if (messageBox && wordCount) {

    function updateWordCount() {

        const text = messageBox.value.trim();

        const words = text
            ? text.split(/\s+/).length
            : 0;

        wordCount.textContent = words + " words";
    }

    messageBox.addEventListener(
        "input",
        updateWordCount
    );

    updateWordCount();
}
