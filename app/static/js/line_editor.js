(function () {
    const DEFAULT_WIDTH = 960;
    const DEFAULT_HEIGHT = 540;

    const img = document.getElementById("video-stream");
    const canvas = document.getElementById("line-canvas");
    const ctx = canvas.getContext("2d");

    const line1Input = document.getElementById("line1-y");
    const line2Input = document.getElementById("line2-y");

    let draggingLine = null;

    function getCanvasSize() {
        const width = img.naturalWidth || DEFAULT_WIDTH;
        const height = img.naturalHeight || DEFAULT_HEIGHT;
        return {width, height};
    }

    function syncCanvasSize() {
        const size = getCanvasSize();

        canvas.width = size.width;
        canvas.height = size.height;

        drawLines();
    }

    function getLineY(lineNumber) {
        if (lineNumber === 1) {
            return Number(line1Input.value || 250);
        }

        return Number(line2Input.value || 340);
    }

    function setLineY(lineNumber, y) {
        y = Math.max(0, Math.min(canvas.height, y));

        if (lineNumber === 1) {
            line1Input.value = Math.round(y);
        } else {
            line2Input.value = Math.round(y);
        }
    }

    function drawSpeedLine(y, color, label) {
        const startX = 80;
        const endX = canvas.width - 80;

        ctx.save();
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.shadowColor = "rgba(0, 0, 0, 0.55)";
        ctx.shadowBlur = 10;
        ctx.lineWidth = 8;
        ctx.strokeStyle = "rgba(15, 23, 42, 0.72)";
        ctx.beginPath();
        ctx.moveTo(startX, y);
        ctx.lineTo(endX, y);
        ctx.stroke();

        ctx.shadowColor = color;
        ctx.shadowBlur = 8;
        ctx.lineWidth = 4;
        ctx.strokeStyle = color;
        ctx.beginPath();
        ctx.moveTo(startX, y);
        ctx.lineTo(endX, y);
        ctx.stroke();

        ctx.shadowBlur = 0;
        ctx.fillStyle = "rgba(15, 23, 42, 0.86)";
        roundRect(ctx, startX + 10, y - 42, 112, 30, 10);
        ctx.fill();

        ctx.fillStyle = color;
        ctx.font = "bold 18px Arial";
        ctx.fillText(label, startX + 24, y - 21);
        ctx.restore();
    }

    function roundRect(ctx, x, y, width, height, radius) {
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.arcTo(x + width, y, x + width, y + height, radius);
        ctx.arcTo(x + width, y + height, x, y + height, radius);
        ctx.arcTo(x, y + height, x, y, radius);
        ctx.arcTo(x, y, x + width, y, radius);
        ctx.closePath();
    }

    function drawLines() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const y1 = getLineY(1);
        const y2 = getLineY(2);

        drawSpeedLine(y1, "#facc15", "测速线 1");
        drawSpeedLine(y2, "#fb7185", "测速线 2");
    }

    function getMousePoint(event) {
        const rect = canvas.getBoundingClientRect();

        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;

        return {
            x: (event.clientX - rect.left) * scaleX,
            y: (event.clientY - rect.top) * scaleY
        };
    }

    function findNearestLine(y) {
        const y1 = getLineY(1);
        const y2 = getLineY(2);

        if (Math.abs(y - y1) <= 15) {
            return 1;
        }

        if (Math.abs(y - y2) <= 15) {
            return 2;
        }

        return null;
    }

    canvas.addEventListener("mousedown", function (event) {
        const point = getMousePoint(event);
        draggingLine = findNearestLine(point.y);

        if (draggingLine) {
            canvas.style.cursor = "grabbing";
        }
    });

    canvas.addEventListener("mousemove", function (event) {
        const point = getMousePoint(event);

        if (draggingLine) {
            setLineY(draggingLine, point.y);
            drawLines();
            return;
        }

        const nearLine = findNearestLine(point.y);
        canvas.style.cursor = nearLine ? "grab" : "default";
    });

    canvas.addEventListener("mouseup", function () {
        draggingLine = null;
        canvas.style.cursor = "grab";
    });

    canvas.addEventListener("mouseleave", function () {
        draggingLine = null;
        canvas.style.cursor = "default";
    });

    line1Input.addEventListener("input", drawLines);
    line2Input.addEventListener("input", drawLines);

    img.addEventListener("load", syncCanvasSize);
    window.addEventListener("resize", drawLines);

    window.getSpeedLinePayload = function () {
        syncCanvasSize();

        const y1 = Number(line1Input.value || 250);
        const y2 = Number(line2Input.value || 340);

        const distance = Number(document.getElementById("distance-m").value || 10);
        const fps = Number(document.getElementById("fps").value || 30);

        return {
            line1: [
                [80, y1],
                [canvas.width - 80, y1]
            ],
            line2: [
                [80, y2],
                [canvas.width - 80, y2]
            ],
            distance_m: distance,
            fps: fps
        };
    };

    window.syncLineCanvas = syncCanvasSize;

    syncCanvasSize();
})();