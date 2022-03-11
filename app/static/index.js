const burgerIcon = document.querySelector('#burger');
const navbarMenu = document.querySelector('#navbarMenuHeroA');

burgerIcon.addEventListener('click', () => {
    navbarMenu.classList.toggle('is-active')
})

