const repoOwner = 'shadowcz007' // 替换为仓库的所有者
const repoName = 'comfyui-mixlab-nodes' // 替换为仓库的名称

const version='v0.2'

fetch(`https://api.github.com/repos/${repoOwner}/${repoName}/releases/latest`)
  .then(response => response.json())
  .then(data => {
    const latestVersion = data.tag_name
    console.log('Latest release version:', latestVersion)
    if(latestVersion!=version){
        window.alert(
            `Please proceed to the official repository to download the latest version.https://github.com/shadowcz007/comfyui-mixlab-nodes/releases/`
          )
          window.open(
            'https://github.com/shadowcz007/comfyui-mixlab-nodes/releases/'
          )
    }
  })
  .catch(error => {
    console.error('Error fetching release information:', error)
  })
//  #MixCopilot
