let index = 0;

function moveSlide(direction) {
  const track = document.querySelector('.carousel-track');
  // Esta línea ahora selecciona tanto las imágenes como los videos
  const slides = document.querySelectorAll('.carousel-track img, .carousel-track video');
  
  index = (index + direction + slides.length) % slides.length;
  track.style.transform = `translateX(-${index * 100}%)`;
}