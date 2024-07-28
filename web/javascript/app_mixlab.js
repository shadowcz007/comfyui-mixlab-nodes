import { app } from '../../../scripts/app.js'
import { $el } from '../../../scripts/ui.js'
import { api } from '../../../scripts/api.js'

import { td_bg } from './td_background.js'
console.log('td_bg', td_bg)
//本机安装的插件节点全集
window._nodesAll = null

//获取当前系统的插件，节点清单
function getObjectInfo () {
  return new Promise(async (resolve, reject) => {
    let url = getUrl()

    try {
      const response = await fetch(`${url}/object_info`)
      const data = await response.json()
      resolve(data)
    } catch (error) {
      reject(error)
    }
  })
}

const base64Df =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAAAXNSR0IArs4c6QAAALZJREFUKFOFkLERwjAQBPdbgBkInECGaMLUQDsE0AkRVRAYWqAByxldPPOWHwnw4OBGye1p50UDSoA+W2ABLPN7i+C5dyC6R/uiAUXRQCs0bXoNIu4QPQzAxDKxHoALOrZcqtiyR/T6CXw7+3IGHhkYcy6BOR2izwT8LptG8rbMiCRAUb+CQ6WzQVb0SNOi5Z2/nX35DRyb/ENazhpWKoGwrpD6nICp5c2qogc4of+c7QcrhgF4Aa/aoAFHiL+RAAAAAElFTkSuQmCC'

const parseImageToBase64 = url => {
  return new Promise((res, rej) => {
    fetch(url)
      .then(response => response.blob())
      .then(blob => {
        const reader = new FileReader()
        reader.onloadend = () => {
          const base64data = reader.result
          res(base64data)
          // 在这里可以将base64数据用于进一步处理或显示图片
        }
        reader.readAsDataURL(blob)
      })
      .catch(error => {
        console.log('发生错误:', error)
      })
  })
}

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
    flexDirection: 'column',
    // alignItems: 'center',
    justifyContent: 'flex-start',
    zIndex: 9999999
  }
}

async function drawImageToCanvas (imageUrl, sFactor = 320) {
  var canvas = document.createElement('canvas')
  var ctx = canvas.getContext('2d')
  var img = new Image()

  await new Promise((resolve, reject) => {
    img.onload = function () {
      var scaleFactor = sFactor / img.width
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

async function extractInputAndOutputData (
  jsonData,
  inputIds = [],
  outputIds = []
) {
  // workflow
  // const workflow=jsonData.workflow;
  // const nodes=workflow.nodes;

  const data = jsonData.output
  let input = []
  let output = []
  const seed = {}
  const seedTitle = {}

  for (const id in data) {
    if (data.hasOwnProperty(id)) {
      let node = app.graph.getNodeById(id)
      if (inputIds.includes(id)) {
        // let node = app.graph.getNodeById(id)
        let options = {}
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

        if (node.type == 'ImagesPrompt_') {
          //图库
          // console.log('ImagesPrompt_', data[id])
          let image_base64 = data[id].inputs.image_base64
          let img_index = 0
          let imgsData = JSON.parse(data[id].inputs.upload)
          for (let index = 0; index < imgsData.length; index++) {
            const imgd = imgsData[index].imgurl
            imgsData[index].index = index
            //TODO缩放大小
            imgsData[index].imgurl = await parseImageToBase64(imgd)
            if (image_base64 == imgsData[index].imgurl) {
              img_index = index
            }
          }
          options.images = imgsData
          delete data[id].inputs.upload
          delete data[id].inputs.image_base64

          data[id].inputs.imageIndex = img_index
        }

        if (node.type == 'Color') {
        }

        // 语音输入的支持
        if (node.type == 'LoadAndCombinedAudio_') {
          // if (
          //   data[id].widgets_values &&
          //   data[id].widgets_values[0] &&
          //   data[id].widgets_values[0].base64 &&
          //   data[id].widgets_values[0].base64.length > 0
          // ) {
          //   options.defaultBase64 = data[id].widgets_values[0].base64
          // }

          input[inputIds.indexOf(id)] = {
            ...data[id],
            title: node.title,
            id,
            options
          }
        }

        if (node.type === 'LoadImage') {
          // loadImage的mask支持
          let output = node.outputs.filter(ot => ot.type == 'MASK')[0]
          if (output.links) {
            // 有输出
            options.hasMask = true
          }
          // loadImage的默认图，转为base64
          let imgurl = app.graph.getNodeById(id).imgs[0].src + '&channel=rgb'

          options.defaultImage = await drawImageToCanvas(imgurl, 512)
          console.log('#loadImage的默认图', options)
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
        let options = {}
        //输出的默认图
        if (
          node.type === 'SaveImageAndMetadata_' &&
          app.graph.getNodeById(id).imgs
        ) {
          // SaveImageAndMetadata_的默认图，转为base64
          let imgurl = app.graph.getNodeById(id).imgs[0].src

          options.defaultImage = await drawImageToCanvas(imgurl, 512)
          console.log('#SaveImageAndMetadata_的默认图', options)
        }

        // let node = app.graph.getNodeById(id)
        // output.push()
        output[outputIds.indexOf(id)] = {
          ...data[id],
          title: node.title,
          id,
          options
        }
      }

      if (
        node.type === 'KSampler' ||
        node.type == 'SamplerCustom' ||
        node.type === 'ChinesePrompt_Mix' ||
        node.type === 'Seed_'
      ) {
        // seed 的类型收集
        try {
          seed[id] = node.widgets.filter(
            w => w.name === 'seed' || w.name == 'noise_seed'
          )[0].linkedWidgets[0].value
          seedTitle[id] = node.title
        } catch (error) {}
      }
    }
  }

  // 修复bug，当节点不存在时
  input = input.filter(i => i)
  output = output.filter(i => i)

  return { input, output, seed, seedTitle }
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
  let nodesAll = window._nodesAll || (await getObjectInfo())

  console.log('####SAVE', nodesAll, json[0])

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

    //从output数据里把工作流的节点，插件数据统计出来
    data.nodesMap = {}
    for (const id in data.output) {
      data.nodesMap[data.output[id].class_type] =
        nodesAll[data.output[id].class_type]
    }

    let { input, output, seed, seedTitle } = await extractInputAndOutputData(
      data,
      inputIds,
      outputIds
    )

    let authorAvatar =
        localStorage.getItem('_mixlab_author_avatar') || base64Df,
      authorName =
        localStorage.getItem('_mixlab_author_name') ||
        localStorage.getItem('Comfy.userName'),
      authorLink = localStorage.getItem('_mixlab_author_link') || ''

    data.app = {
      name,
      description,
      version,
      input,
      output,
      seed, //控制是fixed 还是random
      seedTitle,
      share_prefix,
      link,
      category,
      filename: `${name}_${version}.json`,
      author: {
        avatar: authorAvatar,
        name: authorName,
        link: authorLink
      }
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
      `LoadImage LoadImagesToBatch ImagesPrompt_ LoadAndCombinedAudio_ LoadVideoAndSegment_ VHS_LoadVideo CLIPTextEncode PromptSlide TextInput_ Color FloatSlider IntNumber CheckpointLoaderSimple LoraLoader`.split(
        ' '
      ),
    outputs =
      `SaveTripoSRMesh,PreviewImage,SaveImage,TransparentImage,ShowTextForGPT,CombineAudioVideo,VHS_VideoCombine,VideoCombine_Adv,Image Save,SaveImageAndMetadata_,ClipInterrogator`.split(
        ','
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
  init () {
    if (!window._nodesAll) {
      getObjectInfo().then(r => (window._nodesAll = r))
    }
  },
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
              {...get_position_style(
                ctx,
                widget_width,
                node.size[1] - widget_height,
                node.size[1]
              ),zIndex:1}
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

        //td bg
        const tdBG = document.createElement('button')
        tdBG.innerText = 'Canvas Mode'
        tdBG.style = style
        tdBG.style.marginLeft = '12px'

        tdBG.addEventListener('click', () => {
          td_bg.toggle()
          if (td_bg.running) {
            tdBG.style.background = 'yellow'
          } else {
            tdBG.style.background = 'transparent'
          }
        })

        // author
        let author = document.createElement('div')
        // author.style=`display: flex`

        let authorAvatar = document.createElement('img')
        authorAvatar.className = `${'comfy-multiline-input'}`
        authorAvatar.style = `outline: none;
          border: none;
          padding: 4px;
          width: 32px;
          cursor: pointer;
          height: 32px;`

        if (localStorage.getItem('_mixlab_author_avatar')) {
          authorAvatar.src =
            localStorage.getItem('_mixlab_author_avatar') || base64Df
        }

        let authorAvatarUpload = document.createElement('input')
        authorAvatarUpload.type = 'file'
        authorAvatarUpload.style = `display:none`

        let authorAvatarInput = document.createElement('div')
        authorAvatarInput.style = `display: flex;justify-content: flex-start;
        align-items: center;`
        let authorAvatarInputLabel = document.createElement('p')
        authorAvatarInputLabel.innerText = 'Author Avatar'
        authorAvatarInputLabel.className = `${'comfy-multiline-input'}`
        authorAvatarInputLabel.style = `font-size:12px`

        authorAvatar.addEventListener('click', e => {
          authorAvatarUpload.click()
        })

        authorAvatarInputLabel.addEventListener('click', e => {
          authorAvatarUpload.click()
        })

        authorAvatarUpload.addEventListener('change', event => {
          const file = event.target.files[0]
          const reader = new FileReader()

          reader.onload = async e => {
            let im = new Image()
            im.src = e.target.result
            authorAvatar.src = e.target.result
            im.onload = () => {
              let c = document.createElement('canvas')
              let ctx = c.getContext('2d')
              c.width = 72
              c.height = 72
              ctx.drawImage(
                im,
                0,
                0,
                im.naturalWidth,
                im.naturalHeight,
                0,
                0,
                c.width,
                c.height
              )
              window._mixlab_author_avatar = c.toDataURL()
              localStorage.setItem(
                '_mixlab_author_avatar',
                window._mixlab_author_avatar
              )
            }
          }

          // 以文本形式读取文件
          reader.readAsDataURL(file)
        })

        author.appendChild(authorAvatarInput)
        authorAvatarInput.appendChild(authorAvatarInputLabel)
        authorAvatarInput.appendChild(authorAvatar)
        authorAvatarInput.appendChild(authorAvatarUpload)

        let authorName = document.createElement('input')
        authorName.type = 'text'
        authorName.value =
          localStorage.getItem('_mixlab_author_name') ||
          localStorage.getItem('Comfy.userName')
        authorName.placeholder = 'author name'
        authorName.className = `${'comfy-multiline-input'}`
        authorName.style = `
          outline: none;
          border: none;
          padding: 4px;
          width: 100%;
          cursor: pointer;
          height: 32px;`

        let authorNameInput = document.createElement('div')
        authorNameInput.style = `display: flex;justify-content: flex-start;
          align-items: center;`
        let authorNameInputLabel = document.createElement('p')
        authorNameInputLabel.innerText = 'Author Name'
        authorNameInputLabel.className = `${'comfy-multiline-input'}`
        authorNameInputLabel.style = `font-size:12px;width: 110px`

        authorName.addEventListener('change', e => {
          window._mixlab_author_name = authorName.value.trim()
          localStorage.setItem(
            '_mixlab_author_name',
            window._mixlab_author_name
          )
        })

        author.appendChild(authorNameInput)
        authorNameInput.appendChild(authorNameInputLabel)
        authorNameInput.appendChild(authorName)

        // 社交链接
        let authorLink = document.createElement('input')
        authorLink.type = 'text'
        authorLink.value = localStorage.getItem('_mixlab_author_link') || ''
        authorLink.placeholder = 'author link'
        authorLink.className = `${'comfy-multiline-input'}`
        authorLink.style = `
          outline: none;
          border: none;
          padding: 4px;
          width: 100%;
          cursor: pointer;
          height: 32px;`

        let authorLinkInput = document.createElement('div')
        authorLinkInput.style = `display: flex;justify-content: flex-start;
          align-items: center;`
        let authorLinkInputLabel = document.createElement('p')
        authorLinkInputLabel.innerText = 'Author Link'
        authorLinkInputLabel.className = `${'comfy-multiline-input'}`
        authorLinkInputLabel.style = `font-size:12px;width: 110px`

        authorLink.addEventListener('change', e => {
          window._mixlab_author_link = authorLink.value.trim()
          localStorage.setItem(
            '_mixlab_author_link',
            window._mixlab_author_link
          )
        })

        author.appendChild(authorLinkInput)
        authorLinkInput.appendChild(authorLinkInputLabel)
        authorLinkInput.appendChild(authorLink)

        widget.div.appendChild(author)

        let btns = document.createElement('div')

        widget.div.appendChild(btns)

        btns.appendChild(btn)
        btns.appendChild(download)
        btns.appendChild(tdBG)

        document.body.appendChild(widget.div)
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
          Array.from(div.querySelectorAll('button'), b =>
            b.innerText != 'Canvas Mode' ? (b.style.background = 'yellow') : ''
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

      // app.canvas.centerOnNode(node)
      // app.canvas.setZoom(0.45)
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
