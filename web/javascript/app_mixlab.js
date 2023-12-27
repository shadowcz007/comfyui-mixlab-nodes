import { app } from '../../../scripts/app.js'
import { $el } from '../../../scripts/ui.js'
import { api } from '../../../scripts/api.js'

function get_position_style (ctx, widget_width, y, node_height) {
  const MARGIN = 12 // the margin around the html element

  /* Create a transform that deals with all the scrolling and zooming */
  const elRect = ctx.canvas.getBoundingClientRect()
  const transform = new DOMMatrix()
    .scaleSelf(
      elRect.width / ctx.canvas.width,
      elRect.height / ctx.canvas.height
    )
    .multiplySelf(ctx.getTransform())
    .translateSelf(MARGIN, MARGIN + y)

  return {
    transformOrigin: '0 0',
    transform: transform,
    left: `0`,
    top: `0`,
    cursor: 'pointer',
    position: 'absolute',
    maxWidth: `${widget_width - MARGIN * 2}px`,
    // maxHeight: `${node_height - MARGIN * 2}px`, // we're assuming we have the whole height of the node
    width: `${widget_width - MARGIN * 2}px`,
    // height: `${node_height * 0.3 - MARGIN * 2}px`,
    // background: '#EEEEEE',
    display: 'flex',
    flexDirection: 'row',
    // alignItems: 'center',
    justifyContent: 'flex-start'
  }
}

async function drawImageToCanvas (imageUrl) {
  var canvas = document.createElement('canvas')
  var ctx = canvas.getContext('2d')
  var img = new Image()

  await new Promise((resolve, reject) => {
    img.onload = function () {
      var scaleFactor = 320 / img.width
      var canvasWidth = img.width * scaleFactor
      var canvasHeight = img.height * scaleFactor

      canvas.width = canvasWidth
      canvas.height = canvasHeight

      ctx.drawImage(img, 0, 0, canvasWidth, canvasHeight)

      resolve()
    }

    img.onerror = function () {
      reject(new Error('Failed to load image'))
    }

    img.src = imageUrl
  })

  var base64 = canvas.toDataURL('image/jpeg')
  // console.log(base64); // 输出Base64数据
  return base64
  // 可以在这里执行其他操作，比如将Base64数据保存到服务器或显示在页面上
}

function extractInputAndOutputData (jsonData, inputIds = [], outputIds = []) {
  const data = jsonData
  const input = []
  const output = []

  for (const id in data) {
    if (data.hasOwnProperty(id)) {
      if (inputIds.includes(id)) {
        let node = app.graph.getNodeById(id)
        input[inputIds.indexOf(id)] = { ...data[id], title: node.title, id }
        // input.push()
      }
      if (outputIds.includes(id)) {
        let node = app.graph.getNodeById(id)
        // output.push()
        output[outputIds.indexOf(id)] = { ...data[id], title: node.title, id }
      }
    }
  }

  return { input, output }
}

function getUrl () {
  let api_host = `${window.location.hostname}:${window.location.port}`
  let api_base = ''
  let url = `${window.location.protocol}//${api_host}${api_base}`
  return url
}

async function save_app (json) {
  let url = getUrl()

  const res = await fetch(`${url}/mixlab/workflow`, {
    method: 'POST',
    body: JSON.stringify({
      data: json,
      task: 'save_app'
    })
  })
  return await res.json()
}

function downloadJsonFile (jsonData, fileName = 'mix_app.json') {
  const dataString = JSON.stringify(jsonData)
  const blob = new Blob([dataString], { type: 'application/json' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()

  // 释放URL对象
  setTimeout(() => {
    URL.revokeObjectURL(url)
  }, 0)
}

async function save (json, download = false) {
  const name = json[0],
    version = json[5],
    description = json[4],
    inputIds = json[2].split('\n').filter(f => f),
    outputIds = json[3].split('\n').filter(f => f)

  const iconData = json[1][0]
  let { filename, subfolder, type } = iconData
  let iconUrl = api.apiURL(
    `/view?filename=${encodeURIComponent(
      filename
    )}&type=${type}&subfolder=${subfolder}${app.getPreviewFormatParam()}${app.getRandParam()}`
  )

  try {
    let data = await app.graphToPrompt()

    const { input, output } = extractInputAndOutputData(
      data.output,
      inputIds,
      outputIds
    )

    data.app = {
      name,
      description,
      version,
      input,
      output
    }

    try {
      data.app.icon = await drawImageToCanvas(iconUrl)
    } catch (error) {}
    // console.log(data.app)
    // let http_workflow = app.graph.serialize()

    if (download) {
      await downloadJsonFile(
        data,
        `${data.app.name}_${data.app.version}_${new Date().toDateString()}.json`
      )
      let open = window.confirm(
        `You can now access the standalone application on a new page!\n${getUrl()}/mixlab/app?type=new`
      )
      if (open) window.open(`${getUrl()}/mixlab/app?type=new`)
    } else {
      await save_app(data)

      let open = window.confirm(
        `You can now access the standalone application on a new page!\n${getUrl()}/mixlab/app`
      )
      if (open) window.open(`${getUrl()}/mixlab/app`)
    }
  } catch (error) {
    console.log('###SpeechRecognition', error)
  }
}

app.registerExtension({
  name: 'Mixlab.utils.AppInfo',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'AppInfo') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)
        // console.log(this)
        const widget = {
          type: 'div',
          name: 'AppInfoRun',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(
                ctx,
                widget_width,
                node.widgets[4].last_y + 24,
                node.size[1]
              )
            )
          }
        }

        const style = `
        flex-direction: row;
        background-color: var(--comfy-input-bg);
        border-radius: 8px;
        border-color: var(--border-color);
        border-style: solid;
        color: var(--descrip-text);`

        widget.div = $el('div', {})

        const btn = document.createElement('button')
        btn.innerText = 'Save For App'
        btn.style = style

        btn.addEventListener('click', () => {
          //   console.log('hahhah')
          if (window._mixlab_app_json) {
            save(window._mixlab_app_json)
          } else {
            alert('Please run the workflow before saving')
            // app.queuePrompt(0, 1)
          }
        })

        const download = document.createElement('button')
        download.innerText = 'Download For App'
        download.style = style
        download.style.marginLeft = '12px'

        download.addEventListener('click', () => {
          //   console.log('hahhah')
          if (window._mixlab_app_json) {
            save(window._mixlab_app_json, true)
          } else {
            alert('Please run the workflow before saving')
            // app.queuePrompt(0, 1)
          }
        })

        document.body.appendChild(widget.div)
        widget.div.appendChild(btn)
        widget.div.appendChild(download)

        this.addCustomWidget(widget)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          widget.div.remove()
          return onRemoved?.()
        }

        this.serialize_widgets = true //需要保存参数
      }

      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = async function (message) {
        onExecuted?.apply(this, arguments)
        // console.log(this.widgets)

        window._mixlab_app_json = message.json
        try {
          const div = this.widgets.filter(w => w.div)[0].div
          Array.from(
            div.querySelectorAll('button'),
            b => (b.style.background = 'yellow')
          )
        } catch (error) {}
      }
    }
  }
})
