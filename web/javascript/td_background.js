// touchdesigner的背景效果，把appinfo的输出，选择一张图片作为背景

window._bg_img = null

/**
 * draws the back canvas (the one containing the background and the connections)
 * @method drawBackCanvas
 **/

// 判断是否是新版的，LGraphCanvas.prototype.drawBackCanvas.toString().match('window.devicePixelRatio')
let scale=LGraphCanvas.prototype.drawBackCanvas.toString().match('window.devicePixelRatio')?window.devicePixelRatio:1;

LGraphCanvas.prototype.drawBackCanvas = function () {
  var canvas = this.bgcanvas
  if (
    canvas.width != this.canvas.width ||
    canvas.height != this.canvas.height
  ) {
    canvas.width = this.canvas.width
    canvas.height = this.canvas.height
  }

  if (!this.bgctx) {
    this.bgctx = this.bgcanvas.getContext('2d')
  }
  var ctx = this.bgctx
  if (ctx.start) {
    ctx.start()
  }

  var viewport = this.viewport || [0, 0, ctx.canvas.width, ctx.canvas.height]

  //clear
  if (this.clear_background) {
    ctx.clearRect(viewport[0], viewport[1], viewport[2], viewport[3])
  }

  //show subgraph stack header
  if (this._graph_stack && this._graph_stack.length) {
    ctx.save()
    var parent_graph = this._graph_stack[this._graph_stack.length - 1]
    var subgraph_node = this.graph._subgraph_node
    ctx.strokeStyle = subgraph_node.bgcolor
    ctx.lineWidth = 10
    ctx.strokeRect(1, 1, canvas.width - 2, canvas.height - 2)
    ctx.lineWidth = 1
    ctx.font = '40px Arial'
    ctx.textAlign = 'center'
    ctx.fillStyle = subgraph_node.bgcolor || '#AAA'
    var title = ''
    for (var i = 1; i < this._graph_stack.length; ++i) {
      title += this._graph_stack[i]._subgraph_node.getTitle() + ' >> '
    }
    ctx.fillText(title + subgraph_node.getTitle(), canvas.width * 0.5, 40)
    ctx.restore()
  }

  var bg_already_painted = false
  if (this.onRenderBackground) {
    bg_already_painted = this.onRenderBackground(canvas, ctx)
  }

  //reset in case of error
  if (!this.viewport) {
    ctx.restore()
    // ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.setTransform(scale, 0, 0, scale, 0, 0)
  }
  this.visible_links.length = 0

  if (this.graph) {
    //apply transformations
    ctx.save()
    this.ds.toCanvasContext(ctx)

    //render BG
    if (
      this.ds.scale < 1 &&
      !bg_already_painted &&
      this.clear_background_color
    ) {
      ctx.fillStyle = this.clear_background_color
      ctx.fillRect(
        this.visible_area[0],
        this.visible_area[1],
        this.visible_area[2],
        this.visible_area[3]
      )
    }

    // 主要修改
    if (this.background_image && this.ds.scale > 0.5 && !bg_already_painted) {
      if (this.zoom_modify_alpha) {
        //使得 alpha 越接近0时变化越缓慢。
        let alpha = (1.0 - 0.5 / this.ds.scale) * this.editor_alpha
        ctx.globalAlpha = Math.min(Math.max(0, Math.sqrt(alpha)), 1)
        // console.log((1.0 - 0.5 / this.ds.scale) * this.editor_alpha)
      } else {
        ctx.globalAlpha = this.editor_alpha
      }
      ctx.imageSmoothingEnabled = ctx.imageSmoothingEnabled = false // ctx.mozImageSmoothingEnabled =
      if (!this._bg_img || this._bg_img.name != this.background_image) {
        this._bg_img = new Image()
        this._bg_img.name = this.background_image
        this._bg_img.src = this.background_image
        var that = this
        this._bg_img.onload = function () {
          that.draw(true, true)
        }
      }

      var pattern = null
      if (this._pattern == null && this._bg_img.width > 0) {
        pattern = ctx.createPattern(this._bg_img, 'repeat')
        this._pattern_img = this._bg_img
        this._pattern = pattern
      } else {
        pattern = this._pattern
      }

      if (pattern) {
        ctx.fillStyle = pattern
        ctx.fillRect(
          this.visible_area[0],
          this.visible_area[1],
          this.visible_area[2],
          this.visible_area[3]
        )
        ctx.fillStyle = 'transparent'
      }

      ctx.globalAlpha = 1.0
      ctx.imageSmoothingEnabled = ctx.imageSmoothingEnabled = true //= ctx.mozImageSmoothingEnabled
    }

    //groups
    if (this.graph._groups.length && !this.live_mode) {
      this.drawGroups(canvas, ctx)
    }

    if (this.onDrawBackground) {
      this.onDrawBackground(ctx, this.visible_area)
    }
    if (this.onBackgroundRender) {
      //LEGACY
      console.error(
        'WARNING! onBackgroundRender deprecated, now is named onDrawBackground '
      )
      this.onBackgroundRender = null
    }

    //DEBUG: show clipping area
    //ctx.fillStyle = "red";
    //ctx.fillRect( this.visible_area[0] + 10, this.visible_area[1] + 10, this.visible_area[2] - 20, this.visible_area[3] - 20);

    //bg
    if (this.render_canvas_border) {
      ctx.strokeStyle = '#235'
      ctx.strokeRect(0, 0, canvas.width, canvas.height)
    }

    if (this.render_connections_shadows) {
      ctx.shadowColor = '#000'
      ctx.shadowOffsetX = 0
      ctx.shadowOffsetY = 0
      ctx.shadowBlur = 6
    } else {
      ctx.shadowColor = 'rgba(0,0,0,0)'
    }

    //draw connections
    if (!this.live_mode) {
      this.drawConnections(ctx)
    }

    ctx.shadowColor = 'rgba(0,0,0,0)'

    //restore state
    ctx.restore()
  }

  if (ctx.finish) {
    ctx.finish()
  }

  this.dirty_bgcanvas = false
  this.dirty_canvas = true //to force to repaint the front canvas with the bgcanvas
}

function imgToCanvasBase64 (img) {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  canvas.width = img.width
  canvas.height = img.height
  ctx.drawImage(img, 0, 0)
  const base64 = canvas.toDataURL('image/png')

  return base64
}

// 使用示例
function convertImageToBase64 (img) {
  //   const img = new Image()
  //   img.src = 'path/to/your/image.jpg' // 替换为你的图片路径
  // console.log('convertImageToBase64',img)
  try {
    const base64 = imgToCanvasBase64(img)
    return base64
  } catch (error) {
    console.error(error)
  }
}

function getInputsAndOutputs () {
  const outputs =
    `PreviewImage,SaveImage,TransparentImage,VHS_VideoCombine,VideoCombine_Adv,Image Save,SaveImageAndMetadata_`.split(
      ','
    )

  let outputsId = []

  for (let node of app.graph._nodes) {
    if (outputs.includes(node.type)) {
      outputsId.push(node.id)
    }
  }

  return outputsId
}

function getRandomElement (arr) {
  const randomIndex = Math.floor(Math.random() * arr.length)
  return arr[randomIndex]
}

async function getBG () {
  var outputs = []

  for (let id of app.graph
    .getNodeById(50)
    .widgets.filter(w => w.name === 'output_ids')[0]
    .value.split('\n')) {
    if (getInputsAndOutputs().map(Number).includes(Number(id))) {
      if (app.graph.getNodeById(id).imgs && app.graph.getNodeById(id).imgs[0]) {
        let b = convertImageToBase64(app.graph.getNodeById(id).imgs[0])
        // console.log(b)
        outputs.push(b)
      }
    }
  }

  var BACKGROUND_IMAGE = getRandomElement(outputs),
    CLEAR_BACKGROUND_COLOR = 'rgba(0,0,0,0.9)'

  if (!window._bg_img) {
    window._bg_img = app.canvas._bg_img.src
  }
  // let img=new Image();
  // img.src=BACKGROUND_IMAGE;

  //去掉透明度过度
  // app.canvas.zoom_modify_alpha=false;
  //整体透明度
  app.canvas.editor_alpha = 1.1
  //   app.canvas._pattern=ctx.createPattern(img, "no-repeat");
  app.canvas.updateBackground(BACKGROUND_IMAGE, CLEAR_BACKGROUND_COLOR)
  app.canvas.draw(true, true)
}

class BgRunner {
  constructor () {
    this.intervalId = null
    this.running = false
  }

  // 要运行的方法
  bg () {
    console.log('方法bg正在运行')
    getBG()
  }

  // 启动bg方法每秒运行一次
  start () {
    if (!this.running) {
      this.intervalId = setInterval(() => this.bg(), 1500)
      this.running = true
    }
  }

  // 停止bg方法的运行
  stop () {
    if (this.running) {
      clearInterval(this.intervalId)
      this.intervalId = null
      this.running = false

      if (window._bg_img) {
        var BACKGROUND_IMAGE = window._bg_img,
          CLEAR_BACKGROUND_COLOR = 'rgba(0,0,0,1)'
        app.canvas.editor_alpha = 1

        app.canvas.updateBackground(BACKGROUND_IMAGE, CLEAR_BACKGROUND_COLOR)
        app.canvas.draw(true, true)
      }
    }
  }

  // 切换start和stop
  toggle () {
    if (this.running) {
      this.stop()
    } else {
      this.start()
    }
  }

  // 获取运行状态
  isRunning () {
    return this.running
  }
}

// 示例用法
// const runner = new BgRunner();
// runner.start();
// setTimeout(() => runner.stop(), 5000);

export const td_bg = new BgRunner()
