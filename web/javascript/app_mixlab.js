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
  const seed = {}

  for (const id in data) {
    if (data.hasOwnProperty(id)) {
      let node = app.graph.getNodeById(id)
      if (inputIds.includes(id)) {
        // let node = app.graph.getNodeById(id)
        let options = []
        // 模型
        try {
          if (node.type === 'CheckpointLoaderSimple') {
            options = node.widgets.filter(w => w.name === 'ckpt_name')[0]
              .options.values
          } else if (node.type === 'LoraLoader') {
            options = node.widgets.filter(w => w.name === 'lora_name')[0]
              .options.values
          }
        } catch (error) {}

        if (node.type == 'IntNumber' || node.type == 'FloatSlider') {
          // min max step
          let [v, min, max, step] = Array.from(node.widgets, w => w.value)
          options = { min, max, step }
          // node.widgets.filter(w => w.type === 'number')[0].options
        }

        if (node.type == 'PromptSlide') {
          // min max step
          options = node.widgets.filter(w => w.type === 'slider')[0].options
          // 备选的keywords清单
          try {
            let keywords = node.widgets.filter(w => w.name === 'upload')[0]
              .value
            keywords = JSON.parse(keywords)
            options.keywords = keywords
          } catch (error) {
            console.log(error)
          }
        }

        if (node.type == 'Color') {
        }

        input[inputIds.indexOf(id)] = {
          ...data[id],
          title: node.title,
          id,
          options
        }
        // input.push()
      }
      if (outputIds.includes(id)) {
        // let node = app.graph.getNodeById(id)
        // output.push()
        output[outputIds.indexOf(id)] = { ...data[id], title: node.title, id }
      }

      if (node.type === 'KSampler' || node.type == 'SamplerCustom') {
        // seed 的类型收集
        try {
          seed[id] = node.widgets.filter(
            w => w.name === 'seed' || w.name == 'noise_seed'
          )[0].linkedWidgets[0].value
        } catch (error) {}
      }
    }
  }

  return { input, output, seed }
}

function getUrl () {
  let api_host = `${window.location.hostname}:${window.location.port}`
  let api_base = ''
  let url = `${window.location.protocol}//${api_host}${api_base}`
  return url
}

const getLocalData = key => {
  let data = {}
  try {
    data = JSON.parse(localStorage.getItem(key)) || {}
  } catch (error) {
    return {}
  }
  return data
}

async function save_app (json) {
  let url = getUrl()

  const res = await fetch(`${url}/mixlab/workflow`, {
    method: 'POST',
    body: JSON.stringify({
      data: json,
      task: 'save_app',
      filename: json.app.filename,
      category: json.app.category
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

async function save (json, download = false, showInfo = true) {
  console.log('####SAVE', json[0])
  const name = json[0],
    version = json[5],
    share_prefix = json[6], //用于分享的功能扩展
    link = json[7], //用于创建界面上的跳转链接
    category = json[8] || '', //用于分类
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

    const { input, output, seed } = extractInputAndOutputData(
      data.output,
      inputIds,
      outputIds
    )

    data.app = {
      name,
      description,
      version,
      input,
      output,
      seed, //控制是fixed 还是random
      share_prefix,
      link,
      category,
      filename: `${name}_${version}.json`
    }

    try {
      data.app.icon = await drawImageToCanvas(iconUrl)
    } catch (error) {}
    // console.log(data.app)
    // let http_workflow = app.graph.serialize()
    await save_app(data)
    if (download) {
      await downloadJsonFile(data, data.app.filename)
    }

    if (showInfo) {
      let open = window.confirm(
        `You can now access the standalone application on a new page!\n${getUrl()}/mixlab/app?filename=${encodeURIComponent(
          data.app.filename
        )}&category=${encodeURIComponent(data.app.category)}`
      )
      if (open)
        window.open(
          `${getUrl()}/mixlab/app?filename=${encodeURIComponent(
            data.app.filename
          )}&category=${encodeURIComponent(data.app.category)}`
        )
    }
  } catch (error) {
    console.log('###error', error)
  }
}

function getInputsAndOutputs () {
  const inputs =
      `LoadImage CLIPTextEncode PromptSlide TextInput_ Color FloatSlider IntNumber CheckpointLoaderSimple LoraLoader`.split(
        ' '
      ),
    outputs = `PreviewImage SaveImage ShowTextForGPT VHS_VideoCombine`.split(
      ' '
    )

  let inputsId = [],
    outputsId = []

  for (let node of app.graph._nodes) {
    if (inputs.includes(node.type)) {
      inputsId.push(node.id)
    }

    if (outputs.includes(node.type)) {
      outputsId.push(node.id)
    }
  }

  return {
    input: inputsId,
    output: outputsId
  }
}

app.registerExtension({
  name: 'Mixlab.utils.AppInfo',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'AppInfo') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)
        // console.log('#orig_nodeCreated', this)

        // 自动计算workflow里哪些节点支持
        let input_ids = this.widgets.filter(w => w.name == 'input_ids')[0],
          output_ids = this.widgets.filter(w => w.name == 'output_ids')[0]

        const { input, output } = getInputsAndOutputs()
        input_ids.value = input.join('\n')
        output_ids.value = output.join('\n')

        const widget = {
          type: 'div',
          name: 'AppInfoRun',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(
                ctx,
                widget_width,
                node.size[1] - widget_height,
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
        btn.innerText = 'Save & Open'
        btn.style = style

        btn.addEventListener('click', () => {
          //   console.log('hahhah')
          if (window._mixlab_app_json) {
            save(window._mixlab_app_json)
          } else {
            alert('Please run the workflow before saving')
            // app.queuePrompt(0, 1)
            this.widgets.filter(w => w.name === 'version')[0].value += 1
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
            this.widgets.filter(w => w.name === 'version')[0].value += 1
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

        window._mixlab_app_json = null
      }

      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        onExecuted?.apply(this, arguments)
        console.log(message.json)
        window._mixlab_app_json = message.json
        try {
          let a = this.widgets.filter(w => w.name === 'AppInfoRun')[0]
          if (a) {
            if (!a.value) a.value = 0
            a.value += 1
          }

          const div = this.widgets.filter(w => w.div)[0].div
          Array.from(
            div.querySelectorAll('button'),
            b => (b.style.background = 'yellow')
          )
        } catch (error) {}
      }
    }
  },
  async loadedGraphNode (node, app) {
    // console.log('#loadedGraphNode1111')
    window._mixlab_app_json = null //切换workflow需要清空
    if (node.type === 'AppInfo') {
      let auto_save = node.widgets.filter(w => w.name == 'auto_save')[0]
      if (auto_save) {
        if (!['enable', 'disable'].includes(auto_save.value)) {
          auto_save.value = 'enable'
        }
      }

      app.canvas.centerOnNode(node)
      app.canvas.setZoom(0.45)
    }
  }
})

api.addEventListener('execution_start', async ({ detail }) => {
  console.log('#execution_start', detail)
  window._mixlab_app_json = null
})

api.addEventListener('executed', async ({ detail }) => {
  console.log('#executed', detail)
  // window._mixlab_app_json=null;
  const { output } = getInputsAndOutputs()
  if (output.includes(parseInt(detail.node))) {
    let appinfo = app.graph.findNodesByType('AppInfo')[0]
    if (appinfo) {
      let auto_save = appinfo.widgets.filter(w => w.name == 'auto_save')[0]
      if (auto_save?.value === 'enable') {
        // 自动保存
        console.log('auto_save')
        if (window._mixlab_app_json) save(window._mixlab_app_json, false, false)
      }
    }
  }
})
