function transcribe() {
  const file = document.getElementById("audioFile").files[0];
  const endpoint = "v1/transcribe";
  const formData = new FormData();
  formData.append("file", new Blob([file], { type: file.type }));
  fetch(endpoint, {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      const taskId = data.task_id;
      document.getElementById("taskId").textContent = taskId;
      const taskIdContainer = document.getElementById("taskIdContainer");
      taskIdContainer.style.display = "block";
      const resultContainer = document.getElementById("resultContainer");
      resultContainer.style.display = "block";
      const cleanOutputBtn = document.getElementById("cleanOutputBtn");
      cleanOutputBtn.style.display = "inline-block";
      const statusEndpoint = `v1/status/${taskId}`;
      const interval = setInterval(() => {
        fetch(statusEndpoint)
          .then((response) => response.json())
          .then((data) => {
            if (data.status === "done") {
              clearInterval(interval);
              const resultDiv = document.getElementById("result");
              resultDiv.innerHTML = data.transcript;
            }
          })
          .catch((error) => {
            console.error(error);
            clearInterval(interval);
          });
      }, 1000);
    })
    .catch((error) => {
      console.error(error);
    });
}

function cleanOutput() {
  const taskIdContainer = document.getElementById("taskIdContainer");
  taskIdContainer.style.display = "none";
  const resultContainer = document.getElementById("resultContainer");
  resultContainer.style.display = "none";
  const cleanOutputBtn = document.getElementById("cleanOutputBtn");
  cleanOutputBtn.style.display = "none";
  const resultDiv = document.getElementById("result");
  resultDiv.innerHTML = "";
}
