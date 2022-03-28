function validateFormRace() {
    var formEl = document.forms.race;
    var formData = new FormData(formEl);

    var podium = []
    var keys = ["first", "second", "third"]
    for (const str of keys) {
        value = formData.get(str)
        if (value) {
            podium.push(value)
        }
    }
    form_set = new Set(podium);
    
    if (podium.length != form_set.size){
        alert("Špatně zadaný tip na podium!!!");
        return false;
    };

};
