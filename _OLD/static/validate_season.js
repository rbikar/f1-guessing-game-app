function validateForm() {
    var formEl = document.forms.season;
    var formData = new FormData(formEl);
    form_values = Array.from(formData.values());
    form_set = new Set(form_values);

    if (form_values.length != form_set.size){
        alert("Některý z jezdců/konstruktérů byl zadán vícekrát!!!");
        return false;
    };

};


