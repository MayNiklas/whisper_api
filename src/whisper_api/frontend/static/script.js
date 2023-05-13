// Get DOM elements
const dropArea = document.getElementById("dropArea");
const audioFileInput = document.getElementById("audioFile");
const selectedFileName = document.getElementById("selectedFileName");

// Add click event listener to the drop area to trigger file selection
dropArea.addEventListener("click", () => {
  audioFileInput.click();
});

// Update the selected file name when a file is selected
audioFileInput.addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (file) {
    selectedFileName.innerText = file.name;
  }
});

// Add drag and drop event listeners
dropArea.addEventListener("dragenter", preventDefaults, false);
dropArea.addEventListener("dragleave", preventDefaults, false);
dropArea.addEventListener("dragover", preventDefaults, false);
dropArea.addEventListener("drop", handleDrop, false);

// Prevent default behavior for drag and drop events
function preventDefaults(event) {
  event.preventDefault();
  event.stopPropagation();
}

// Add/remove highlight class on dragenter and dragleave events
dropArea.addEventListener("dragenter", () => {
  dropArea.classList.add("highlight");
}, false);
dropArea.addEventListener("dragleave", () => {
  dropArea.classList.remove("highlight");
}, false);

// Handle the drop event
function handleDrop(event) {
  preventDefaults(event);

  const dt = event.dataTransfer;
  const file = dt.files[0];

  // Remove the highlight class and set the input's files property
  dropArea.classList.remove("highlight");
  audioFileInput.files = dt.files;

  // Update the selected file name
  selectedFileName.innerText = file.name;

  // Automatically start the transcription
  transcribe();
}

function transcribe() {
  // Clear the output container
  const outputContainer = document.getElementById("resultContainer");
  outputContainer.style.display = "none";
  outputContainer.querySelector("#result").innerHTML = "";

  // Get the selected file
  const fileInput = document.getElementById("audioFile");
  const file = fileInput.files[0];
  if (!file) {
    alert("Please select an audio file.");
    return;
  }

  // Create a FormData object and append the file to it
  const formData = new FormData();
  formData.append("file", file, file.name);

  // Send a POST request to the server to initiate transcription
  fetch("/api/v1/transcribe", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      // Display the task ID
      const taskIdContainer = document.getElementById("taskIdContainer");
      const taskId = document.getElementById("taskId");
      taskId.innerText = data.task_id;
      taskIdContainer.style.display = "block";

      // Check the status of the transcription every second
      const intervalId = setInterval(() => {
        fetch(`/api/v1/status?task_id=${data.task_id}`)
          .then((response) => response.json())
          .then((data) => {
            if (data.status === "finished") {
              // Display the transcription
              clearInterval(intervalId);
              const resultContainer = document.getElementById("resultContainer");
              const result = document.getElementById("result");
              result.innerText = data.transcript;
              resultContainer.style.display = "block";
              document.getElementById("cleanOutputBtn").style.display = "block";
              taskIdContainer.style.display = "none";

              // Remove the content of the file variable after transcription
              fileInput.value = "";
            }
          });
      }, 1000);
    })
    .catch((error) => {
      console.error("Error:", error);
    });
}

function cleanOutput() {
  // Get the output container and hide it
  const outputContainer = document.getElementById("resultContainer");
  outputContainer.style.display = "none";

  // Clear the result content
  outputContainer.querySelector("#result").innerHTML = "";

  // Hide the clean output button
  document.getElementById("cleanOutputBtn").style.display = "none";

  // Hide the task ID container and clear its content
  const taskIdContainer = document.getElementById("taskIdContainer");
  taskIdContainer.style.display = "none";
  taskIdContainer.querySelector("#taskId").innerHTML = "";

  // Reset the selected file name
  selectedFileName.innerText = "No file selected";
}
