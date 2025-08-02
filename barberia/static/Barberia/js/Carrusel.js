let index = 0;

function moveSlide(direction) {
  const track = document.querySelector('.carousel-track');
  const slides = document.querySelectorAll('.carousel-track img');
  index = (index + direction + slides.length) % slides.length;
  track.style.transform = `translateX(-${index * 100}%)`;
}