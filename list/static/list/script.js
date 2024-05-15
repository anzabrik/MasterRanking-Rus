document.addEventListener('DOMContentLoaded', function () {
    if (document.querySelectorAll('.add-book')) {
        document.querySelectorAll('.add-book').forEach(btn => {
            btn.onclick = () => {
                listId = btn.id.substring(1);
                document.querySelector(`#f${listId}`).style.display = 'block';
                btn.style.display = 'none';
                document.querySelector(`#c${listId}`).style.display = 'block';
                document.querySelector(`#c${listId}`).onclick = () => {
                    document.querySelector(`#f${listId}`).style.display = 'none';
                    btn.style.display = 'block';
                    document.querySelector(`#c${listId}`).style.display = 'none';
                }
            }
            document.querySelector('#save-book').onclick = () => {
                document.querySelector(`#f${listId}`).style.display = 'none';
                btn.style.display = 'block';
                document.querySelector(`#c${listId}`).style.display = 'none';
            }
        });
    }

    $(function () {
        $('[data-toggle="tooltip"]').tooltip()
    })

    if (document.querySelector('#master-edit-btn')) {
        editMasterName();
    }
})


function editMasterName() {
    editBtn = document.querySelector('#master-edit-btn')
    editBtn.onclick = () => {
        // Hide "edit master" & "delete master" buttons
        document.querySelector("#master-btns").style.display = 'none';

        let nameh1 = document.querySelector('#master-name');
        let masterName = nameh1.innerHTML;
        let masterId = nameh1.dataset.masterid;

        // Replace master name with text input+save button
        nameh1.innerHTML = `<form id="hell"><textarea>${masterName}</textarea><br><input type="submit" value="Save" class="btn btn-primary"></form>`;
        document.querySelector('#hell').onsubmit = () => {
            // Bring back "edit master" & "delete master" buttons
            document.querySelector("#master-btns").style.display = 'block';
            // Get new name from the form
            let newName = document.querySelector('textarea').value;
            // Display new name on the page
            nameh1.innerHTML = newName;
            // Put request to replace name in master obj on server
            fetch(`/masters/edit/${masterId}`, {
                method: 'PUT',
                body: JSON.stringify({
                    master_name: newName
                })
            })
            return false;
        }
    }
}
