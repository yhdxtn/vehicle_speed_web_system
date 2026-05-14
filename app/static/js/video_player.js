(function () {
    const img = document.getElementById("video-stream");

    window.startVideoStream = function () {
        img.src = "/api/video/stream?t=" + Date.now();
    };

    window.stopVideoStream = function () {
        img.removeAttribute("src");
    };
})();