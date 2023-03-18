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
  fetch("/v1/transcribe", {
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
    })
    .catch((error) => {
      console.error("Error:", error);
    });
}

function cleanOutput() {
  const outputContainer = document.getElementById("resultContainer");
  outputContainer.style.display = "none";
  outputContainer.querySelector("#result").innerHTML = "";
  document.getElementById("cleanOutputBtn").style.display = "none";
  const taskIdContainer = document.getElementById("taskIdContainer");
  taskIdContainer.style.display = "none";
  taskIdContainer.querySelector("#taskId").innerHTML = "";
}
