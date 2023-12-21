import { app } from '../../../scripts/app.js'
// import { api } from '../../../scripts/api.js'
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
    width: `${widget_width - MARGIN * 2}px`,
    // height: `${node_height * 0.3 - MARGIN * 2}px`,
    // background: '#EEEEEE',
    display: 'flex',
    flexDirection: 'column',
    // alignItems: 'center',
    justifyContent: 'space-around'
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

function speakText (text) {
  const speechMsg = new SpeechSynthesisUtterance()
  speechMsg.text = text

  // 语音合成结束时触发的事件
  speechMsg.onend = function (event) {
    console.log('语音播放结束')
    window._mixlab_speech_synthesis_onend = true
  }

  // 语音合成错误时触发的事件
  speechMsg.onerror = function (event) {
    console.error('语音播放错误:', event.error)
  }

  // 使用浏览器默认语音合成器进行语音播放
  speechSynthesis.speak(speechMsg)
}

// 调用方法，将文字转换为语音播放
// speakText('Hello, how are you?');
//                      #MixCopilot

const start = (element, id, startBtn) => {

  startBtn.className='loading_mixlab'

  window.recognition = new webkitSpeechRecognition()

  window.recognition.continuous = true
  window.recognition.interimResults = true
  window.recognition.lang = navigator.language

  let timeoutId, intervalId

  window.recognition.onstart = () => {
    console.log('开始语音输入', window._mixlab_speech_synthesis_onend)
    window._mixlab_speech_synthesis_onend = false
  }

  window.recognition.onresult = function (event) {
    const result = event.results[event.results.length - 1][0].transcript
    console.log('识别结果：', result)
    element.value = result

    let data = getLocalData('_mixlab_speech_recognition')
    data[id] = result.trim()
    localStorage.setItem('_mixlab_speech_recognition', JSON.stringify(data))

    if (timeoutId) clearTimeout(timeoutId)
   
    if (!window.recognition) return

    timeoutId = setTimeout(function () {
      console.log('结果传递：：', result)
      app.queuePrompt(0, 1)
      window.recognition?.stop()
      window.recognition = null;
      startBtn.className=''
      startBtn.innerText = 'START'
      

      timeoutId = null

      intervalId = setInterval(() => {
        if (
          app.ui.lastQueueSize === 0 &&
          !window.recognition &&
          window._mixlab_speech_synthesis_onend
        ) {
          start(element, id, startBtn)
          startBtn.innerText = 'STOP'
          if (intervalId) {
            clearInterval(intervalId)
          }
        }
      }, 2200)
    }, 2000)
  }

  window.recognition.onend = function () {
    console.log('语音输入结束')
  }

  window.recognition.onspeechend = function () {
    console.log('onspeechend')
  }

  window.recognition.onerror = function (event) {
    console.log('Error occurred in recognition: ' + event.error)
  }

  window.recognition.start()
}

app.registerExtension({
  name: 'Mixlab.audio.SpeechRecognition',
  async getCustomWidgets (app) {
    return {
      AUDIOINPUTMIX (node, inputName, inputData, app) {
        // console.log('##node', node)
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 32], // a default size
          draw (ctx, node, width, y) {},
          computeSize (...args) {
            return [128, 32] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            let data = getLocalData('_mixlab_speech_recognition')
            return data[node.id] || 'Hello Mixlab'
          }
        }
        //  widget.something = something;          // maybe adds stuff to it
        node.addCustomWidget(widget) // adds it to the node
        return widget // and returns it.
      }
    }
  },

  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'SpeechRecognition') {
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)

        const widget = {
          type: 'div',
          name: 'chatgptdiv',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width, 44, node.size[1])
            )
          }
        }

        widget.div = $el('div', {})

        document.body.appendChild(widget.div)

        const inputDiv = (key, placeholder) => {
          let div = document.createElement('div')
          const startBtn = document.createElement('button')
          const textArea = document.createElement('textarea')

          textArea.className = `${'comfy-multiline-input'} ${placeholder}`

          textArea.style = `margin-top: 14px;
          height: 44px;`

          div.style = `flex-direction: column;
          display: flex;
          margin: 0px 8px 6px;`

          startBtn.style = `
          background-color: var(--comfy-input-bg);
          border-radius: 8px;
          border-color: var(--border-color);
          border-style: solid;
          color: var(--descrip-text);
          `

          startBtn.innerText = 'START'

          div.appendChild(startBtn)
          div.appendChild(textArea)

          startBtn.addEventListener('click', () => {
            if (window.recognition) {
              window.recognition.stop()
              window.recognition = null
              startBtn.innerText = 'START'
              startBtn.className=''
            } else {
              start(textArea, this.id, startBtn)
              startBtn.innerText = 'STOP'
            }
          })

          return div
        }

        let inputAudio = inputDiv('_mixlab_speech_recognition', 'audio')
        widget.div.appendChild(inputAudio)

        this.addCustomWidget(widget)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          inputAudio.remove()
          widget.div.remove()
          return onRemoved?.()
        }

        this.serialize_widgets = true //需要保存参数
      }
    }
  },
  async loadedGraphNode (node, app) {
    if (node.type === 'SpeechRecognition') {
      let data = getLocalData('_mixlab_speech_recognition')
      // console.log('_mixlab_speech_recognition', node.widgets)
      let div = node.widgets.filter(f => f.type === 'div')[0]
      if (div && data[node.id]) {
        div.div.querySelector('textarea').value = data[node.id]
      }
    }
  }
})

app.registerExtension({
  name: 'Mixlab.audio.SpeechSynthesis',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeData.name === 'SpeechSynthesis') {
      function populate (text) {
        // console.log('SpeechSynthesis',this.widgets)

        if (this.widgets) {
          const pos = this.widgets.findIndex(w => w.name === 'text')
          if (pos !== -1) {
            for (let i = pos; i < this.widgets.length; i++) {
              this.widgets[i].onRemove?.()
            }
            this.widgets.length = pos
          }
        }

        for (let list of text) {
          const w = ComfyWidgets['STRING'](
            this,
            'text',
            ['STRING', { multiline: true }],
            app
          ).widget
          w.inputEl.readOnly = true
          w.inputEl.style.opacity = 0.6
          w.value = list
        }

        speakText(text.join('\n'))

        // console.log('ShowTextForGPT',this.widgets.length)
        requestAnimationFrame(() => {
          const sz = this.computeSize()
          if (sz[0] < this.size[0]) {
            sz[0] = this.size[0]
          }
          if (sz[1] < this.size[1]) {
            sz[1] = this.size[1]
          }
          this.onResize?.(sz)
          app.graph.setDirtyCanvas(true, false)
        })
      }

      // When the node is executed we will be sent the input text, display this in the widget
      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        onExecuted?.apply(this, arguments)
        populate.call(this, message.text)
      }

      this.serialize_widgets = true //需要保存参数
    }
  }
})
