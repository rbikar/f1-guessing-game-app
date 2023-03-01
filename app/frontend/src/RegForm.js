import { useForm } from "react-hook-form";
import bcrypt from "bcryptjs";
import { redirect, useNavigate } from "react-router-dom";


export default function RegForm() {
    const { register, handleSubmit, formState: { errors, }} = useForm({ shouldUseNativeValidation: true });
    const navigate = useNavigate();
    const onSubmit = (data, e) => {
      e.preventDefault()

      var salt = bcrypt.genSaltSync(10);
      var hash = bcrypt.hashSync(data.password, salt);
      register_user(data.username, hash).then( redirect("/current_bet"));
      navigate("/")
     

    }

    async function register_user(username, hash) {
      const requestOptions = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username,
                               password: hash })
    };
      console.log(requestOptions)

      //const response = await fetch('/api/register', requestOptions);
      //if (!response.ok) {
      //  console.log(response)
      //  alert("Nelze registrovat")
      //  return (<h1>Test</h1>)
        
     // }
   //   const response_data = await response.json();

     // console.log(response_data)
     
    }


    return (
      <form onSubmit={handleSubmit(onSubmit)}>
        <input name="username" placeholder="Uzivatelske jmeno" {...register("username", { pattern: { value: /^[A-Za-z0-9]+$/i, message: 'Invalid'}, required: true })} />
        <input type="password" placeholder="Heslo" {...register("password", {required: true})} />
        <input type="password" {...register("password_check", {required: true})} />
        <input type="submit" />
      </form>
    );

}
