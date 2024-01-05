import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'

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

              // widget.value = keywords
              let ks = getLocalData(`_mixlab_PromptSlide`)
              ks[this.id] = keywords
              setLocalDataOfWin(`_mixlab_PromptSlide`, ks)

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
        let ks = getLocalData(`_mixlab_PromptSlide`)

        let keywords = ks[node.id]
        // console.log('keywords',keywords)
        let widget = node.widgets.filter(w => w.select)[0]
        if (keywords && keywords[0]) {
          // let widget = node.widgets.filter(w => w.select)[0]
          // console.log('select',widget,widget.value)
          widget.select.style.display = 'block'
          createSelect(widget.select, keywords, prompt)
        }
      } catch (error) {}
    }
  }
})

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
              justifyContent: 'flex-start'
            })
          }
        }

        widget.div = $el('div', {})

        document.body.appendChild(widget.div)

        this.addCustomWidget(widget)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          widget.div.remove()
          return onRemoved?.()
        }

        // this.serialize_widgets = true //需要保存参数
      }

      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        onExecuted?.apply(this, arguments)
        console.log('PromptImage', message.prompts, message._images)
        // window._mixlab_app_json = message.json
        try {
          let widget = this.widgets.filter(w => w.name === 'result')[0]

          widget.div.innerHTML = ``

          for (let index = 0; index < message._images.length; index++) {
            const img = message._images[index]
            let url = api.apiURL(
              `/view?filename=${encodeURIComponent(img.filename)}&type=${
                img.type
              }&subfolder=${
                img.subfolder
              }${app.getPreviewFormatParam()}${app.getRandParam()}`
            )

            // 创建card
            let div = document.createElement('div')
            div.style = `width: 150px;`
            div.innerHTML = `<img src="${url}" style='width: 100%'/><p style="margin: 0;
            font-size: 12px;
            position: relative;
            margin-top: -35px;
            background: #8080808f;">${message.prompts[index]}</p>`
            widget.div.appendChild(div)
          }
        } catch (error) {}
      }
    }
  }
})
