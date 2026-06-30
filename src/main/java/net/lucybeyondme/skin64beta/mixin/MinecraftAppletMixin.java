package net.lucybeyondme.skin64beta.mixin;

import net.minecraft.client.MinecraftApplet;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(MinecraftApplet.class)
public class MinecraftAppletMixin {
	@Inject(at = @At("RETURN"), method = "init", remap = false)
	private void init(CallbackInfo ci) {
		System.out.println("This line is printed by an example mod mixin!");
	}
}
