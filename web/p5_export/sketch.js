function setup () {
  createCanvas(400, 400, WEBGL)
  angleMode(DEGREES)
}

function draw () {
  if (frameCount === 1) {
    capturer.start()
  }

  background(30)
  noStroke()
  translate(0, 0, sin(frameCount) * 400 - 800)

  rotateX(frameCount)
  rotateY(frameCount)
  rotateZ(frameCount)

  var w = 20

  randomSeed(1)
  for (var x = -width / 2; x <= width / 2; x += w) {
    for (var y = -width / 2; y <= width / 2; y += w) {
      for (var z = -width / 2; z <= width / 2; z += w) {
        var r = random(255)
        var g = random(255)
        var b = random(255)

        fill(r, g, b)

        push()
        translate(x, y, z)
        box(w)
        pop()
      }
    }
  }
  // console.log(frameRate());

  if (frameCount < 60) {
    capturer.capture(canvas)
  } else if (frameCount === 60) {
    capturer.save(function (blob) {
        // console.log(blob)

        // 示例用法
        // const blob = new Blob([/* 数据 */], { type: 'video/webm' });
        blobToBase64(blob).then(base64String => {
            console.log(base64String);
         
            const video = document.createElement('video');
            video.controls = true; // 显示视频控件（播放、暂停等）
            video.src = base64String; // 设置视频的 src 属性为 Base64 数据 URL
            video.width = 640; // 设置视频宽度
            video.height = 360; // 设置视频高度

            // 将 video 元素添加到页面中
            document.body.appendChild(video)

            // 自动播放视频
            video.play();

        }).catch(error => {
            console.error('转换失败:', error);
        });

    })
    capturer.stop()
  }
}
