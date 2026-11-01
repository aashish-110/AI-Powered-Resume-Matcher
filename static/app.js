const input = document.querySelector('#resumes');
const dropZone = document.querySelector('#drop-zone');
const fileList = document.querySelector('#file-list');
const form = document.querySelector('#upload-form');
const submitButton = document.querySelector('#submit-button');

function showFiles(files) {
  fileList.innerHTML = '';
  [...files].forEach((file) => {
    const item = document.createElement('div');
    item.className = 'file-item';
    const extension = file.name.split('.').pop().toUpperCase();
    const type = document.createElement('span');
    type.className = 'file-type';
    type.textContent = extension;
    const name = document.createElement('span');
    name.textContent = file.name;
    const size = document.createElement('small');
    size.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
    item.append(type, name, size);
    fileList.appendChild(item);
  });
}

input.addEventListener('change', () => showFiles(input.files));
['dragenter', 'dragover'].forEach((eventName) => dropZone.addEventListener(eventName, (event) => {
  event.preventDefault();
  dropZone.classList.add('dragging');
}));
['dragleave', 'drop'].forEach((eventName) => dropZone.addEventListener(eventName, (event) => {
  event.preventDefault();
  dropZone.classList.remove('dragging');
}));
dropZone.addEventListener('drop', (event) => {
  input.files = event.dataTransfer.files;
  showFiles(input.files);
});
form.addEventListener('submit', () => {
  submitButton.disabled = true;
  submitButton.querySelector('span').textContent = 'Analyzing…';
});
