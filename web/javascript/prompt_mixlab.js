import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'

import PhotoSwipeLightbox from '/extensions/comfyui-mixlab-nodes/lib/photoswipe-lightbox.esm.min.js'
function loadCSS (url) {
  var link = document.createElement('link')
  link.rel = 'stylesheet'
  link.type = 'text/css'
  link.href = url
  document.getElementsByTagName('head')[0].appendChild(link)

  // Create a style element
  const style = document.createElement('style')
  // Define the CSS rule for scrollbar width
  const cssRule = `.pswp__custom-caption {
    background: rgb(20 27 70);
    font-size: 16px;
    color: #fff;
    width: calc(100% - 32px);
    max-width: 980px;
    padding: 2px 8px;
    border-radius: 4px;
    position: absolute;
    left: 50%;
    bottom: 16px;
    transform: translateX(-50%);
  }
  .pswp__custom-caption a {
    color: #fff;
    text-decoration: underline;
  }
  .hidden-caption-content {
    display: none;
  }`
  // Add the CSS rule to the style element
  style.appendChild(document.createTextNode(cssRule))

  // Append the style element to the document head
  document.head.appendChild(style)
}
loadCSS('/extensions/comfyui-mixlab-nodes/lib/photoswipe.min.css')

function initLightBox () {
  const lightbox = new PhotoSwipeLightbox({
    gallery: '.prompt_image_output',
    children: 'a',
    pswpModule: () =>
      import('/extensions/comfyui-mixlab-nodes/lib/photoswipe.esm.min.js')
  })

  lightbox.on('uiRegister', function () {
    lightbox.pswp.ui.registerElement({
      name: 'custom-caption',
      order: 9,
      isButton: false,
      appendTo: 'root',
      html: 'Caption text',
      onInit: (el, pswp) => {
        lightbox.pswp.on('change', () => {
          const currSlideElement = lightbox.pswp.currSlide.data.element
          let captionHTML = ''
          if (currSlideElement) {
            const hiddenCaption = currSlideElement.querySelector(
              '.hidden-caption-content'
            )
            if (hiddenCaption) {
              // get caption from element with class hidden-caption-content
              captionHTML = hiddenCaption.innerHTML
            } else {
              // get caption from alt attribute
              captionHTML = currSlideElement
                .querySelector('img')
                .getAttribute('alt')
            }
          }
          el.innerHTML = captionHTML || ''
        })
      }
    })
  })

  lightbox.init()
}

function get_position_style (ctx, widget_width, y, node_height) {
  const MARGIN = 4 // the margin around the html element

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
    width: `${widget_width - MARGIN * 2 - 24}px`,
    // height: `${node_height * 0.3 - MARGIN * 2}px`,
    // background: '#EEEEEE',
    paddingLeft: '12px',
    display: 'flex',
    flexDirection: 'row',
    // alignItems: 'center',
    justifyContent: 'space-between'
  }
}
function createImage (url) {
  let im = new Image()
  return new Promise((res, rej) => {
    im.onload = () => res(im)
    im.src = url
  })
}

async function fetchImage (url) {
  try {
    const response = await fetch(url)
    const blob = await response.blob()

    return blob
  } catch (error) {
    console.error('出现错误:', error)
  }
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

const setLocalDataOfWin = (key, value) => {
  localStorage.setItem(key, JSON.stringify(value))
  // window[key] = value
}

const createSelect = (select, opts, targetWidget) => {
  select.style.display = 'block'
  let html = ''
  let isMatch = false
  for (const opt of opts) {
    html += `<option value='${opt}' ${
      targetWidget.value === opt ? 'selected' : ''
    }>${opt}</option>`
    if (targetWidget.value === opt) isMatch = true
  }
  select.innerHTML = html
  if (!isMatch) targetWidget.value = opts[0]
  // 添加change事件监听器
  select.addEventListener('change', function () {
    // 获取选中的选项的值
    var selectedOption = select.options[select.selectedIndex].value
    targetWidget.value = selectedOption
    // console.log(widget,selectedOption)
  })
}

app.registerExtension({
  name: 'Mixlab.prompt.RandomPrompt',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'RandomPrompt') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = async function () {
        orig_nodeCreated?.apply(this, arguments)
        name

        const mutable_prompt = this.widgets.filter(
          w => w.name == 'mutable_prompt'
        )[0]
        // console.log('PromptSlide nodeData', prompt_keyword)

        const widget = {
          type: 'div',
          name: 'upload',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width, y, node.size[1])
            )
          }
        }

        widget.div = $el('div', {})

        const btn = document.createElement('button')
        btn.innerText = 'Upload Keywords'

        btn.style = `cursor: pointer;
        font-weight: 300;
        margin: 2px; 
        color: var(--descrip-text);
        background-color: var(--comfy-input-bg);
        border-radius: 8px;
        border-color: var(--border-color);
        border-style: solid;    height: 30px;min-width: 122px;
       `

        // const btn=document.createElement('button');
        // btn.innerText='Upload'
        btn.addEventListener('click', () => {
          let inp = document.createElement('input')
          inp.type = 'file'
          inp.accept = '.txt'
          inp.click()
          inp.addEventListener('change', event => {
            // 获取选择的文件
            const file = event.target.files[0]
            this.title = file.name.split('.')[0]

            // console.log(file.name.split('.')[0])
            // 创建文件读取器
            const reader = new FileReader()

            // 定义读取完成事件的回调函数
            reader.onload = event => {
              // 读取完成后的文本内容
              const fileContent = event.target.result.split('\n')
              const keywords = Array.from(fileContent, f => f.trim()).filter(
                f => f
              )
              // 打印文件内容
              //   console.log(keywords)

              mutable_prompt.value = keywords.join('\n')

              inp.remove()
            }

            // 以文本方式读取文件
            reader.readAsText(file)
          })
        })

        widget.div.appendChild(btn)
        document.body.appendChild(widget.div)
        this.addCustomWidget(widget)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          widget.div.remove()
          return onRemoved?.()
        }

        if (this.onResize) {
          this.onResize(this.size)
        }

        this.serialize_widgets = true //需要保存参数
      }
    }
  },
  async loadedGraphNode (node, app) {
    if (node.type === 'RandomPrompt') {
      // try {
      //   let mutable_prompt = node.widgets.filter(w => w.name === 'mutable_prompt')[0]
      //   // let ks = getLocalData(`_mixlab_PromptSlide`)
      //   let uploadWidget = node.widgets.filter(w => w.name == 'upload')[0]
      //   // console.log('##widget', uploadWidget.value)
      //   let keywords = JSON.parse(uploadWidget.value)
      //   if (keywords && keywords[0]) {
      //     mutable_prompt.value=keywords.join('\n')
      //   }
      // } catch (error) {}
    }
  }
})

app.registerExtension({
  name: 'Mixlab.prompt.PromptSlide',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'PromptSlide') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = async function () {
        orig_nodeCreated?.apply(this, arguments)

        const prompt_keyword = this.widgets.filter(
          w => w.name == 'prompt_keyword'
        )[0]
        // console.log('PromptSlide nodeData', prompt_keyword)

        const widget = {
          type: 'div',
          name: 'upload',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width, y, node.size[1])
            )
          }
        }

        widget.div = $el('div', {})

        const btn = document.createElement('button')
        btn.innerText = 'Upload Keywords'

        btn.style = `cursor: pointer;
        font-weight: 300;
        margin: 2px; 
        color: var(--descrip-text);
        background-color: var(--comfy-input-bg);
        border-radius: 8px;
        border-color: var(--border-color);
        border-style: solid;    height: 30px;min-width: 122px;
       `

        const select = document.createElement('select')
        select.style = `display:none;cursor: pointer;
        font-weight: 300;
        margin: 2px; 
        color: var(--descrip-text);
        background-color: var(--comfy-input-bg);
        border-radius: 8px;
        border-color: var(--border-color);
        border-style: solid;    height: 30px;min-width: 100px;
       `
        widget.select = select

        // const btn=document.createElement('button');
        // btn.innerText='Upload'
        btn.addEventListener('click', () => {
          let inp = document.createElement('input')
          inp.type = 'file'
          inp.accept = '.txt'
          inp.click()
          inp.addEventListener('change', event => {
            // 获取选择的文件
            const file = event.target.files[0]
            this.title = file.name.split('.')[0]

            // console.log(file.name.split('.')[0])
            // 创建文件读取器
            const reader = new FileReader()

            // 定义读取完成事件的回调函数
            reader.onload = event => {
              // 读取完成后的文本内容
              const fileContent = event.target.result.split('\n')
              const keywords = Array.from(fileContent, f => f.trim()).filter(
                f => f
              )
              // 打印文件内容
              //   console.log(keywords)

              widget.value = JSON.stringify(keywords)

              // let ks = getLocalData(`_mixlab_PromptSlide`)
              // ks[this.id] = keywords
              // setLocalDataOfWin(`_mixlab_PromptSlide`, ks)

              createSelect(select, keywords, prompt_keyword)

              inp.remove()
            }

            // 以文本方式读取文件
            reader.readAsText(file)
          })
        })

        widget.div.appendChild(btn)
        widget.div.appendChild(select)
        document.body.appendChild(widget.div)
        this.addCustomWidget(widget)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          widget.div.remove()
          return onRemoved?.()
        }

        if (this.onResize) {
          this.onResize(this.size)
        }

        this.serialize_widgets = true //需要保存参数
      }
    }
  },
  async loadedGraphNode (node, app) {
    if (node.type === 'PromptSlide') {
      try {
        let prompt = node.widgets.filter(w => w.name === 'prompt_keyword')[0]
        // let ks = getLocalData(`_mixlab_PromptSlide`)
        let uploadWidget = node.widgets.filter(w => w.name == 'upload')[0]
        // console.log('##widget', uploadWidget.value)
        let keywords = JSON.parse(uploadWidget.value)
        // console.log('keywords',keywords)
        let widget = node.widgets.filter(w => w.select)[0]
        if (keywords && keywords[0]) {
          widget.select.style.display = 'block'
          createSelect(widget.select, keywords, prompt)
        }
      } catch (error) {}
    }
  }
})

const _createResult = async (node, widget, message) => {
  widget.div.innerHTML = ``

  const width = node.size[0] * 0.5 - 12

  let height_add = 0

  for (let index = 0; index < message._images.length; index++) {
    const imgs = message._images[index]

    for (const img of imgs) {
      let url = api.apiURL(
        `/view?filename=${encodeURIComponent(img.filename)}&type=${
          img.type
        }&subfolder=${
          img.subfolder
        }${app.getPreviewFormatParam()}${app.getRandParam()}`
      )

      let image = await createImage(url)

      // 创建card
      let div = document.createElement('div')
      div.className = 'card'
      div.draggable = true

      div.ondragend = async event => {
        console.log('拖动停止')
        let url = div.querySelector('img').src

        let blob = await fetchImage(url)

        let imageNode = null
        // No image node selected: add a new one
        if (!imageNode) {
          const newNode = LiteGraph.createNode('LoadImage')
          newNode.pos = [...app.canvas.graph_mouse]
          imageNode = app.graph.add(newNode)
          app.graph.change()
        }

        // const blob = item.getAsFile();
        imageNode.pasteFile(blob)
      }

      div.setAttribute('data-scale', image.naturalHeight / image.naturalWidth)

      let h = (image.naturalHeight * width) / image.naturalWidth
      if (index % 2 === 0) height_add += h
      div.style = `width: ${width}px;height:${h}px;position: relative;margin: 4px;`

      div.innerHTML = `<a href="${url}" 
      data-pswp-width="${image.naturalWidth}" 
      data-pswp-height="${image.naturalHeight}" 
      target="_blank">
      <img src="${url}" style='width: 100%' alt="${message.prompts[index]}"/>
    </a>
    <p style="position: absolute;
            bottom: 0;
            left: 0;
            opacity: 0.6;
            background-color: var(--comfy-input-bg); 
            color: var(--descrip-text);
            margin: 0;
            font-size: 12px;
            padding: 5px;
            text-align: left;">${message.prompts[index]}</p>`
      widget.div.appendChild(div)
    }
  }

  node.size[1] = 98 + height_add
}

app.registerExtension({
  name: 'Mixlab.prompt.PromptImage',

  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'PromptImage') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)
        console.log('#orig_nodeCreated', this)
        const widget = {
          type: 'div',
          name: 'result',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(this.div.style, {
              ...get_position_style(ctx, widget_width, y, node.size[1]),
              flexWrap: 'wrap',
              justifyContent: 'space-between',
              // outline: '1px solid red',
              paddingLeft: '0px',
              width: widget_width + 'px'
            })
          }
        }

        widget.div = $el('div', {})
        widget.div.className = 'prompt_image_output'

        document.body.appendChild(widget.div)

        this.addCustomWidget(widget)

        initLightBox()

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          widget.div.remove()
          return onRemoved?.()
        }

        const onResize = this.onResize
        this.onResize = function () {
          // 缩放发生
          // console.log('##缩放发生', this.size)
          let w = this.size[0] * 0.5 - 12
          Array.from(widget.div.querySelectorAll('.card'), card => {
            card.style.width = `${w}px`
            card.style.height = `${
              w * parseFloat(card.getAttribute('data-scale'))
            }px`
          })
          return onResize?.apply(this, arguments)
        }

        // this.serialize_widgets = true //需要保存参数
      }

      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = async function (message) {
        onExecuted?.apply(this, arguments)
        console.log('#PromptImage', message.prompts, message._images)
        // window._mixlab_app_json = message.json
        try {
          let widget = this.widgets.filter(w => w.name === 'result')[0]
          widget.value = message
          _createResult(this, widget, { ...message })
        } catch (error) {
          console.log(error)
        }
      }

      this.serialize_widgets = true //需要保存参数
    }
  },
  async loadedGraphNode (node, app) {
    if (node.type === 'PromptImage') {
      // await sleep(0)
      let widget = node.widgets.filter(w => w.name === 'result')[0]
      console.log('widget.value', widget.value)

      initLightBox()

      let cards = widget.div.querySelectorAll('.card')
      if (cards.length == 0) node.size = [280, 120]

      _createResult(node, widget, widget.value)
    }
  }
})
