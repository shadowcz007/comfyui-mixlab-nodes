;(() => {
  let div = document.createElement('div')

  div.innerHTML = ` 
    <div id="app-login">
        <div class="login-app-view">
            <header class="app-header">
                <h1>Hi</h1>
                Welcome back,<br />
                <span class="app-subheading">
                    sign in to continue<br />
    
                </span>
            </header>
            <input class="email" type="email" required pattern=".*\.\w{2,}" placeholder="Email Address" />
            <input class="password" type="password" required placeholder="Password" />
            <a class="app-button" id="login_run">登录</a>
            <!-- <div class="app-register">
                Don't have an account? <a>Sign Up</a>
            </div> -->
            <svg id="svg-lines" version="1.1" xmlns="http://www.w3.org/2000/svg"
                xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" viewBox="0 0 284.2 152.7"
                xml:space="preserve">
                <path class="st0"
                    d="M37.7,107.3h222.6c12,0,21.8,9.7,21.8,21.7s-9.7,21.8-21.8,21.8c0,0-203.6,0-222.6,0S2.2,138.6,2.2,103.3   c0-52,113.5-101.5,141-101.5c13.5,0,21.8,9.7,21.8,21.8s-9.7,21.7-21.8,21.7s-21.8-9.7-21.8-21.7s9.7-21.8,21.8-21.8" />
                <path class="st1"
                    d="M260.2,76.3L250,87.8l-9-9c-6.2-6.2,2-24.7,17.2-24.7c15.2,0,23.9,17.7,23.9,29.7s-11.7,23.5-23.9,23.5h-10.2">
                </path>
                <g class="svg-loader" xmlns="http://www.w3.org/2000/svg">
                    <path class="svg-loader-segment -cal" d="M164.7,23.5c0-12-9.7-21.8-21.8-21.8" />
                    <path class="svg-loader-segment -heart" d="M143,45.2c12,0,21.8-9.7,21.8-21.7" />
                    <path class="svg-loader-segment -steps" d="M121.2,23.5c0,12,9.7,21.7,21.8,21.7" />
                    <path class="svg-loader-segment -temp" d="M143,1.7c-12,0-21.8,9.7-21.8,21.8" />
                </g>
            </svg>
        </div>
    </div>
    <div class="login-background"></div>
     `

  document.body.appendChild(div)
  let bg = div.querySelector('.login-background')
  bg.addEventListener('click', e => {
    div.style.display = 'none'
  })
  let login_btn = document.body.querySelector('#login_btn')
  // login_btn.href="";
  login_btn.innerHTML =
    '<svg stroke="currentColor" fill="none" stroke-width="0" viewBox="0 0 24 24" height="40px" width="40px" xmlns="http://www.w3.org/2000/svg"><path d="M12 17C14.2091 17 16 15.2091 16 13H8C8 15.2091 9.79086 17 12 17Z" fill="currentColor"></path><path d="M10 10C10 10.5523 9.55228 11 9 11C8.44772 11 8 10.5523 8 10C8 9.44772 8.44772 9 9 9C9.55228 9 10 9.44772 10 10Z" fill="currentColor"></path><path d="M15 11C15.5523 11 16 10.5523 16 10C16 9.44772 15.5523 9 15 9C14.4477 9 14 9.44772 14 10C14 10.5523 14.4477 11 15 11Z" fill="currentColor"></path><path fill-rule="evenodd" clip-rule="evenodd" d="M22 12C22 17.5228 17.5228 22 12 22C6.47715 22 2 17.5228 2 12C2 6.47715 6.47715 2 12 2C17.5228 2 22 6.47715 22 12ZM20 12C20 16.4183 16.4183 20 12 20C7.58172 20 4 16.4183 4 12C4 7.58172 7.58172 4 12 4C16.4183 4 20 7.58172 20 12Z" fill="currentColor"></path></svg>LOGIN'
  login_btn.addEventListener('click', e => {
    e.preventDefault()
    div.style.display = 'block'
  })
  let login_run = div.querySelector('#login_run')
  login_run.addEventListener('click', e => {
    e.preventDefault()
    let ps = div.querySelector('.password')
    let email = div.querySelector('.email')
    div.style.display = 'none'
    console.log(ps.value, email.value)
  })
})()
