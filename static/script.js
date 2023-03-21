document.addEventListener("DOMContentLoaded", () => {
  const dropArea = document.getElementById("dropArea");

  dropArea.addEventListener("dragover", handleDragOver);
  dropArea.addEventListener("drop", handleDrop);
  dropArea.addEventListener("click", handleClick);

  function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    dropArea.classList.add("dragging");
  }

  function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    dropArea.classList.remove("dragging");

    if (event.dataTransfer.items && event.dataTransfer.items.length > 0) {
      const file = event.dataTransfer.items[0].getAsFile();
      if (file) {
        transcribe(file);
      } else {
        alert("Please drop a valid audio file.");
      }
    }
  }

  function handleClick() {
    const fileInput = document.getElementById("audioFile");
    fileInput.click();
  }
});

function transcribe(file) {
  // Create a FormData object
  const formData = new FormData();

  // Check if a file is provided
  if (file) {
    // Append the provided file to FormData
    formData.append("file", file, file.name);
  } else {
    // Get the file input and selected file
    const fileInput = document.getElementById("audioFile");
    const selectedFile = fileInput.files[0];

    // Check if a file is selected
    if (!selectedFile) {
      alert("Please select an audio file.");
      return;
    }

    // Append the selected file to FormData
    formData.append("file", selectedFile, selectedFile.name);
  }

  // Create a new XMLHttpRequest
  const xhr = new XMLHttpRequest();

  // Handle the upload progress
  xhr.upload.addEventListener("progress", (event) => {
    if (event.lengthComputable) {
      // Show the progress container and update the progress bar width
      const progressContainer = document.getElementById("progressContainer");
      progressContainer.style.display = "block";
      const progressBar = document.getElementById("progress");
      const progressPercentage = Math.round((event.loaded / event.total) * 100);
      progressBar.style.width = `${progressPercentage}%`;
    }
  });

  // Handle the load event
  xhr.addEventListener("load", () => {
    // Parse the response JSON
    const data = JSON.parse(xhr.responseText);

    // Display the task ID
    const taskIdContainer = document.getElementById("taskIdContainer");
    const taskId = document.getElementById("taskId");
    taskId.innerText = data.task_id;
    taskIdContainer.style.display = "block";

    // Show "upload done!" with a green checkmark
    const uploadStatus = document.getElementById("uploadStatus");
    uploadStatus.style.display = "block";
    setTimeout(() => {
      uploadStatus.style.display = "none";
    }, 3000);

    // Check the status of the transcription every second
    const intervalId = setInterval(() => {
      fetch(`/v1/status/${data.task_id}`)
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "done") {
            // Display the transcription
            clearInterval(intervalId);
            const resultContainer = document.getElementById("resultContainer");
            const result = document.getElementById("result");
            result.innerText = data.transcript;
            resultContainer.style.display = "block";
            document.getElementById("cleanOutputBtn").style.display = "block";
            taskIdContainer.style.display = "none";
          }
        });
    }, 1000);
  });

  // Handle errors
  xhr.addEventListener("error", () => {
    console.error("Error:", xhr.statusText);
  });

  // Open and send the request
  xhr.open("POST", "/v1/transcribe");
  xhr.send(formData);
}

function cleanOutput() {
  const outputContainer = document.getElementById("resultContainer");
  outputContainer.style.display = "none";
  outputContainer.querySelector("#result").innerHTML = "";
  document.getElementById("cleanOutputBtn").style.display = "none";
  const taskIdContainer = document.getElementById("taskIdContainer");
  taskIdContainer.style.display = "none";
  taskIdContainer.querySelector("#taskId").innerHTML = "";

  // Clear the selected file name
  const fileNameDisplay = document.getElementById("selectedFileName");
  fileNameDisplay.textContent = "";
}

// Add event listeners for drag and drop events
const dropArea = document.getElementById("dropArea");
const fileInput = document.getElementById("audioFile");

dropArea.addEventListener("click", (event) => {
  fileInput.click();
});

dropArea.addEventListener("dragover", (event) => {
  event.preventDefault();
  event.stopPropagation();
  dropArea.classList.add("drop-area-hover");
});

dropArea.addEventListener("dragleave", (event) => {
  event.preventDefault();
  event.stopPropagation();
  dropArea.classList.remove("drop-area-hover");
});

dropArea.addEventListener("drop", (event) => {
  event.preventDefault();
  event.stopPropagation();
  dropArea.classList.remove("drop-area-hover");

  const files = event.dataTransfer.files;
  if (files.length) {
    const file = files[0];
    handleFileInput(file);

    // Automatically start the transcription
    transcribe();
  }
});

// Add event listener for file input change
fileInput.addEventListener("change", (event) => {
  const files = event.target.files;
  if (files.length) {
    const file = files[0];
    handleFileInput(file);
  } else {
    handleFileInput(null);
  }
});
