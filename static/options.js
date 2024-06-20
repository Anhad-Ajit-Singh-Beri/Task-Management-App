function savecategorys(categorys) {
    chrome.storage.local.set({ savedcategorys: categorys });
}

function loadcategorys(callback) {
    chrome.storage.local.get('savedcategorys', function (result) {
        const categorys = result.savedcategorys || [];
        callback(categorys);
    });
}

let savedcategorys;
let savedTemplates;

function initialize() {
    loadcategorys(function (categorys) {
        savedcategorys = categorys;
        rendercategorys();
    });
}

function rendercategorys() {
    const categorysList = document.getElementById('categorysList');
    categorysList.innerHTML = '';
    savedcategorys.forEach(category => {
        const listItem = document.createElement('li');
        listItem.innerHTML = `
            <div>
                <img src="${category.image || 'https://via.placeholder.com/40'}" alt="Avatar">
                <span>${category.name || category.email}</span>
            </div>
            <div>
                <button class="edit-button" data-email="${category.email}">Edit</button>
                <button class="delete-button" data-email="${category.email}">Delete</button>
            </div>
        `;
        categorysList.appendChild(listItem);
    });

    const editButtons = document.querySelectorAll('.edit-button');
    editButtons.forEach(button => {
        button.addEventListener('click', () => {
            editcategory(button.getAttribute('data-email'));
        });
    });

    const deleteButtons = document.querySelectorAll('.delete-button');
    deleteButtons.forEach(button => {
        button.addEventListener('click', () => {
            deletecategory(button.getAttribute('data-email'));
        });
    });
}

function editcategory(email) {
    const category = savedcategorys.find(category => category.email === email);
    if (!category) return;

    document.getElementById('categoryEmail').value = category.email;
    document.getElementById('categoryName').value = category.name || '';
    document.getElementById('categoryImageUrl').value = '';
    document.getElementById('editcategoryModal').style.display = 'flex';
}

document.getElementById('savecategory').addEventListener('click', () => {
    const email = document.getElementById('categoryEmail').value;
    const name = document.getElementById('categoryName').value;
    const imageUpload = document.getElementById('categoryImageUpload').files[0];
    const imageUrl = document.getElementById('categoryImageUrl').value;

    let image = '';

    if (imageUpload) {
        const reader = new FileReader();
        reader.onload = function (e) {
            image = e.target.result;
            updatecategory(email, name, image);
        };
        reader.readAsDataURL(imageUpload);
    } else {
        image = imageUrl;
        updatecategory(email, name, image);
    }

    document.getElementById('editcategoryModal').style.display = 'none';
});

const updatecategory = (email, name, image) => {
    const categoryIndex = savedcategorys.findIndex(category => category.email === email);
    if (categoryIndex > -1) {
        savedcategorys[categoryIndex].name = name;
        savedcategorys[categoryIndex].image = image;
    } else {
        savedcategorys.push({ email, name, image });
    }
    savecategorys(savedcategorys);
    rendercategorys();
};

function deletecategory(email) {
    savedcategorys = savedcategorys.filter(category => category.email !== email);
    savecategorys(savedcategorys);
    rendercategorys();
}

document.getElementById('addcategoryButton').addEventListener('click', () => {
    document.getElementById('categoryEmail').value = '';
    document.getElementById('categoryName').value = '';
    document.getElementById('categoryImageUrl').value = '';
    document.getElementById('editcategoryModal').style.display = 'flex';
});

const categoryModal = document.getElementById('editcategoryModal');
const closecategoryModal = categoryModal ? categoryModal.getElementsByClassName('close')[0] : null;

if (closecategoryModal) {
    closecategoryModal.onclick = function () {
        categoryModal.style.display = 'none';
    };
}


window.onclick = function (event) {
    categoryModal.style.display = 'none';
}

initialize();