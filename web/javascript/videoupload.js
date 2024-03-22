import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'

function videoUpload (node, inputName, inputData, app) {
  const imageWidget = node.widgets.find(w => w.name === 'video')
  let uploadWidget

  const displayDiv = document.createElement('video')
  console.log('imageWidget', node)

  var default_value = imageWidget.value
  Object.defineProperty(imageWidget, 'value', {
    set: function (value) {
      this._real_value = value
    },

    get: function () {
      let value = ''
      if (this._real_value) {
        value = this._real_value
      } else {
        return default_value
      }

      if (value.filename) {
        let real_value = value
        value = ''
        if (real_value.subfolder) {
          value = real_value.subfolder + '/'
        }

        value += real_value.filename

        if (real_value.type && real_value.type !== 'input')
          value += ` [${real_value.type}]`
      }
      return value
    }
  })
  async function uploadFile (file, updateNode, pasted = false) {
    try {
      // Wrap file in formdata so it includes filename
      const body = new FormData()
      body.append('image', file)
      if (pasted) body.append('subfolder', 'pasted')
      const resp = await api.fetchApi('/upload/image', {
        method: 'POST',
        body
      })

      if (resp.status === 200) {
        const data = await resp.json()
        // Add the file to the dropdown list and update the widget value
        let path = data.name
        if (data.subfolder) path = data.subfolder + '/' + path

        if (!imageWidget.options.values.includes(path)) {
          imageWidget.options.values.push(path)
        }

        if (updateNode) {
          imageWidget.value = path
        }
      } else {
        alert(resp.status + ' - ' + resp.statusText)
      }
    } catch (error) {
      alert(error)
    }
  }

  const fileInput = document.createElement('input')
  Object.assign(fileInput, {
    type: 'file',
    accept: 'video/webm,video/mp4,video/mkv,image/gif',
    style: 'display: none',
    onchange: async () => {
      if (fileInput.files.length) {
        let file = fileInput.files[0]
        console.log(file)
        await uploadFile(file, true)
      }
    }
  })
  document.body.append(fileInput)

  // Create the button widget for selecting the files
  uploadWidget = node.addWidget('button', 'upload file', 'video', () => {
    fileInput.click()
  })
  uploadWidget.serialize = false
  return { widget: uploadWidget }
}
ComfyWidgets.VIDEOUPLOAD_ = videoUpload


app.registerExtension({
  name: 'Mixlab.Video.LoadVideoAndSegment_',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeData?.name == 'LoadVideoAndSegment_') {
      nodeData.input.required.upload = ['VIDEOUPLOAD_'];

    //   const onExecuted = nodeType.prototype.onExecuted
    //   nodeType.prototype.onExecuted = function (message) {
    //     onExecuted?.apply(this, arguments)
    //     console.log(message)
        
    //     // try {
    //     //   let a = this.widgets.filter(w => w.name === 'AppInfoRun')[0]
    //     //   if (a) {
    //     //     if (!a.value) a.value = 0
    //     //     a.value += 1
    //     //   }

    //     //   const div = this.widgets.filter(w => w.div)[0].div
    //     //   Array.from(
    //     //     div.querySelectorAll('button'),
    //     //     b => (b.style.background = 'yellow')
    //     //   )
    //     // } catch (error) {}
    //   }

    }
  }
})
